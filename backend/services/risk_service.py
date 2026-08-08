"""
DarpanAI — Risk Service (Ensemble v2 — 12-Feature ICMR)
=========================================================
Replaced the old XGBoost single-output model with the new
DarpanTransformer + XGBoost + meta-learner ensemble trained on ICMR data.

Now produces 3 disease-specific risk scores (Diabetes, CVD, Hypertension)
plus a composite risk score, instead of a single opaque number.

Composite score thresholds (calibrated to ICMR output range):
  0–20   → Low
  20–40  → Moderate
  40–60  → High
  60–100 → Critical
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from backend.db.postgres import get_db
from backend.services.ensemble_service import predict_risk


async def compute_risk(user_id: str, log_id: str, normalized: dict) -> Dict[str, Any]:
    """
    Runs the DarpanEnsemble on the user's latest health snapshot.

    Args:
        user_id:    DarpanAI user identifier
        log_id:     health_log row ID (for audit trail)
        normalized: normalized feature dict from ingestion_service

    Returns:
        {
          "risk_score":        float,   # composite (0–100)
          "risk_category":     str,
          "top_risk_factors":  list,
          "diabetes_risk":     float,
          "cvd_risk":          float,
          "hypertension_risk": float,
          "raw_features":      dict,
        }
    """
    pool = get_db()
    async with pool.acquire() as conn:

        # Fetch the full raw snapshot from health_logs (most recent for this log_id)
        row = await conn.fetchrow(
            """
            SELECT heart_rate, sleep, steps, bmi, stress_level, diet_score, extras,
                   heart_rate_norm, steps_norm, sleep_norm, bmi_norm,
                   stress_level_norm, diet_score_norm
            FROM health_logs
            WHERE log_id = $1
            """,
            log_id,
        )

        # Last 30 CALENDAR DAYS (not rows) → a real sequence for the transformer
        # instead of tiling today 30x (HC-05).
        #
        # DISTINCT ON collapses same-day submissions to the latest one before
        # the outer LIMIT ever sees them. Without this, a burst of repeated
        # manual check-ins (double-clicking "Analyze," a slider resubmitted
        # unchanged) counts as N separate "days" in the window instead of one
        # — which is exactly what fed the transformer 16 duplicate rows during
        # this session and helped trigger the saturation fallback on data that
        # should have looked like 14 clean days, not 30 noisy ones.
        history_rows = await conn.fetch(
            """
            SELECT DISTINCT ON ((timestamp AT TIME ZONE 'UTC')::date)
                   heart_rate, steps, sleep, bmi, stress_level, diet_score, extras
            FROM health_logs
            WHERE user_id = $1
            ORDER BY (timestamp AT TIME ZONE 'UTC')::date DESC, timestamp DESC
            LIMIT 30
            """,
            user_id,
        )

        # Pull full clinical profile from users table
        user_row = await conn.fetchrow(
            """
            SELECT age, gender, whr, fam_diabetes, fam_cvd, fam_hypertension
            FROM users WHERE user_id = $1
            """,
            user_id,
        )
        age            = float(user_row["age"])            if (user_row and user_row["age"]            is not None) else 35.0
        gender_raw     = user_row["gender"]                if (user_row and user_row["gender"]         is not None) else None
        gender         = 1 if str(gender_raw).lower() in ("male", "m", "1") else 0
        whr            = float(user_row["whr"])            if (user_row and user_row["whr"]            is not None) else 0.85
        fam_diabetes   = int(user_row["fam_diabetes"])     if (user_row and user_row["fam_diabetes"]   is not None) else 0
        fam_cvd        = int(user_row["fam_cvd"])          if (user_row and user_row["fam_cvd"]        is not None) else 0
        fam_hypertension = int(user_row["fam_hypertension"]) if (user_row and user_row["fam_hypertension"] is not None) else 0

    # Build raw snapshot — health vitals + clinical profile fields
    profile_fields = {
        "gender":           gender,
        "whr":              whr,
        "fam_diabetes":     fam_diabetes,
        "fam_cvd":          fam_cvd,
        "fam_hypertension": fam_hypertension,
    }

    if row:
        snapshot = {
            "heart_rate":       float(row["heart_rate"]   if row["heart_rate"]   is not None else 72),
            # sleep=0 from a daytime sync means "not yet recorded" — use 7h neutral for risk model
            "sleep":            float(row["sleep"] if row["sleep"] not in (None, 0) else 7),
            "steps":            float(row["steps"]         if row["steps"]         is not None else 8000),
            "bmi":              float(row["bmi"]           if row["bmi"]           is not None else 23.5),
            "stress_level":     float(row["stress_level"]  if row["stress_level"]  is not None else 4),
            "diet_score":       float(row["diet_score"]    if row["diet_score"]    is not None else 6),
            **profile_fields,
        }
        # Device-measured HRV / sugar override the derived proxies (HC-03/HC-04)
        snapshot.update(_extras_of(row))
    else:
        snapshot = _denorm_snapshot(normalized)
        snapshot.update(profile_fields)

    history = [_merge_extras(dict(r)) for r in history_rows]

    # Ensemble inference is CPU-bound (torch + 3 XGBoost) — keep it off the loop
    result = await asyncio.to_thread(predict_risk, snapshot, age, history)

    composite_risk    = result["composite_risk"]
    risk_category     = result["risk_category"]
    top_risk_factors  = result["top_risk_factors"]

    # Persist to risk_scores table
    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO risk_scores (
                user_id, log_id, risk_score, risk_category, top_risk_factors,
                shap_contributions, primary_cause, causal_chain, model_version,
                raw_features, timestamp
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9,
                $10, $11
            )
            """,
            user_id,
            log_id,
            round(composite_risk, 2),
            risk_category,
            json.dumps(top_risk_factors),
            json.dumps({                           # pre-fill with ensemble disease scores
                "diabetes_risk":     result["diabetes_risk"],
                "cvd_risk":          result["cvd_risk"],
                "hypertension_risk": result["hypertension_risk"],
            }),
            top_risk_factors[0] if top_risk_factors else "",
            "",                                    # causal_chain filled by causal_service
            "darpan_ensemble_v2_12feature",
            json.dumps({
                **snapshot, "age": age,
                # No schema migration needed — raw_features is already a JSONB
                # scratch bag for exactly this kind of per-request diagnostic.
                "sequence_source":          result["sequence_source"],
                "n_real_days":              result["n_real_days"],
                "model_saturated":          result["model_saturated"],
                "saturated_after_fallback": result["saturated_after_fallback"],
            }),
            now,
        )

    return {
        "risk_score":        round(composite_risk, 2),
        "risk_category":     risk_category,
        "top_risk_factors":  top_risk_factors,
        "diabetes_risk":     result["diabetes_risk"],
        "cvd_risk":          result["cvd_risk"],
        "hypertension_risk": result["hypertension_risk"],
        "raw_features":      {**snapshot, "age": age},
        # Provenance — how much real history backed this score
        "sequence_source":   result["sequence_source"],
        "n_real_days":       result["n_real_days"],
        # Saturation disclosure — surfaced through the API, not silently clipped
        "model_saturated":          result["model_saturated"],
        "saturated_after_fallback": result["saturated_after_fallback"],
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pj(val, default):
    """Parse a JSONB column — asyncpg may return str or already-decoded."""
    if val is None:
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


# Device-measured fields that override derived proxies when present
_MEASURED_KEYS = ("hrv_rmssd", "sugar_intake_g")


def _extras_of(row) -> dict:
    """Pull only the measured overrides out of a row's extras JSONB."""
    extras = _pj(row["extras"] if "extras" in row.keys() else None, {}) or {}
    return {k: extras[k] for k in _MEASURED_KEYS if extras.get(k) is not None}


def _merge_extras(row: dict) -> dict:
    """Lift measured overrides from extras onto the row, then drop extras."""
    extras = _pj(row.pop("extras", None), {}) or {}
    for key in _MEASURED_KEYS:
        if extras.get(key) is not None:
            row[key] = extras[key]
    return row



_DENORM_BOUNDS = {
    "heart_rate":   (40,  200),
    "steps":        (0,   20000),
    "sleep":        (0,   12),
    "bmi":          (15,  50),
    "stress_level": (1,   10),
    "diet_score":   (1,   10),
}


def _denorm_snapshot(normalized: dict) -> dict:
    """Convert normalized [0,1] values back to raw units."""
    result = {}
    for field, (lo, hi) in _DENORM_BOUNDS.items():
        val = normalized.get(field, 0.5)
        result[field] = round(lo + val * (hi - lo), 2)
    return result
