"""
Explainability Service — SHAP over the live DarpanEnsemble.

WHAT THIS EXPLAINS, PRECISELY
-----------------------------
The ensemble is: Transformer + 3 XGBoost specialists → Ridge meta-learner.
SHAP's TreeExplainer works on trees, so it explains the XGBoost specialists,
not the transformer. That is a partial explanation — but it is an *exactly
quantified* partial explanation, not a hand-wave, because the meta-learner is
linear:

    output_d = Σ_h W_t[d,h]·transformer_h + Σ_h W_x[d,h]·xgb_h + intercept_d

So for output d, the contribution of the 36 engineered features via head h is
exactly W_x[d,h] · shap_h. Summing over h gives the true XGBoost-attributable
portion of that disease score, and the remainder is the transformer's share.
We report both, plus `explained_fraction`, so the UI can state honestly how
much of the score SHAP accounts for. On the shipped weights the XGBoost heads
carry ~63-75% of each disease output.

Attributions are grouped from the 36 engineered features (mean/std/min/max/
trend per dynamic feature, plus threshold counts) back onto the 12 base ICMR
features by summation — the standard treatment for grouped SHAP.

Units are risk-score points on the same 0-100 scale as the displayed score,
signed: positive = pushes risk up, negative = protective.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

import numpy as np

from backend.db.postgres import get_db
from backend.services.ensemble_service import (
    COMPOSITE_WEIGHTS,
    DISEASE_SCALE,
    DISEASES,
    ICMR_TO_LEGACY,
    XGB_BASE_OF,
    XGB_FEATURE_NAMES,
    _extract_xgb_features,
    build_sequence_from_history,
    build_sequence_from_snapshot,
    get_ensemble,
)

# Human-readable labels for the 12 base ICMR features
FEATURE_LABELS = {
    "age":              "Age",
    "gender":           "Sex",
    "bmi":              "BMI",
    "whr":              "Waist-Hip Ratio",
    "fam_diabetes":     "Family History — Diabetes",
    "fam_cvd":          "Family History — Cardiovascular",
    "fam_hypertension": "Family History — Hypertension",
    "sleep_hours":      "Sleep Duration",
    "steps":            "Daily Steps",
    "sugar_intake_g":   "Sugar Intake",
    "stress_level":     "Stress Level",
    "hrv_rmssd":        "Heart Rate Variability",
}

DISEASE_LABELS = {
    "diabetes_risk":     "Type 2 Diabetes",
    "cvd_risk":          "Cardiovascular Disease",
    "hypertension_risk": "Hypertension",
}

# Features the user cannot change — excluded from "what should I do" ranking
NON_MODIFIABLE = {
    "age", "gender", "fam_diabetes", "fam_cvd", "fam_hypertension",
}

_explainers: Optional[Dict[str, Any]] = None


def _get_explainers() -> Dict[str, Any]:
    """One SHAP TreeExplainer per XGBoost specialist, built once."""
    global _explainers
    if _explainers is None:
        import shap
        heads = get_ensemble().xgb_heads
        _explainers = {d: shap.TreeExplainer(heads[d]) for d in DISEASES}
    return _explainers


def _pj(val, default):
    """Parse a JSONB column — asyncpg may hand back str or already-decoded."""
    if val is None:
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _group_to_base(shap_36: np.ndarray) -> Dict[str, float]:
    """
    Collapse the 36 engineered-feature attributions onto the 12 base ICMR
    features. Summation is correct here: SHAP values are additive, so the
    contribution of "sleep" is the sum of its mean/std/min/max/trend/threshold
    attributions.
    """
    grouped: Dict[str, float] = {}
    for value, base in zip(shap_36, XGB_BASE_OF):
        grouped[base] = grouped.get(base, 0.0) + float(value)
    return grouped


def _explain_sequence(sequence: List[dict]) -> Dict[str, Any]:
    """
    Blocking SHAP computation — callers must run this in a worker thread.

    Returns per-disease grouped attributions in final-output risk points, the
    composite attribution, and the transformer/XGBoost split.
    """
    ensemble   = get_ensemble()
    explainers = _get_explainers()

    x     = ensemble.to_array(sequence)       # [1, 30, 12]
    parts = ensemble.decompose(x)
    x_xgb = parts["xgb_input"]                # [1, 36]

    W_x = ensemble.meta_xgb_weights()         # [3, 3] output x head
    W_t = ensemble.meta_transformer_weights() # [3, 3]

    # SHAP for each head, in that head's own output units
    head_shap: Dict[str, np.ndarray] = {}
    head_base: Dict[str, float] = {}
    for disease in DISEASES:
        ex = explainers[disease]
        head_shap[disease] = np.asarray(ex.shap_values(x_xgb), dtype=np.float64).reshape(-1)
        head_base[disease] = float(np.ravel(ex.expected_value)[0])

    per_disease: Dict[str, Any] = {}
    composite_36 = np.zeros(36, dtype=np.float64)

    for d_idx, disease in enumerate(DISEASES):
        scale = DISEASE_SCALE[disease]

        # Exact XGBoost-attributable portion of this output, in output units,
        # then calibrated to the same scale as the displayed score.
        attributed = np.zeros(36, dtype=np.float64)
        for h_idx, head in enumerate(DISEASES):
            attributed += W_x[d_idx, h_idx] * head_shap[head]
        attributed *= scale

        # How much of the score SHAP accounts for vs the transformer
        xgb_share = float(
            sum(W_x[d_idx, h] * parts["xgb_preds"][0, h] for h in range(3))
        ) * scale
        transformer_share = float(
            sum(W_t[d_idx, h] * parts["transformer_preds"][0, h] for h in range(3))
        ) * scale
        total = float(parts["ensemble_out"][0, d_idx]) * scale
        denom = abs(xgb_share) + abs(transformer_share)

        grouped = _group_to_base(attributed)
        per_disease[disease] = {
            "label":              DISEASE_LABELS[disease],
            "score":             round(total, 2),
            "contributions":     {k: round(v, 3) for k, v in grouped.items()},
            "xgb_component":     round(xgb_share, 2),
            "transformer_component": round(transformer_share, 2),
            "explained_fraction": round(abs(xgb_share) / denom, 3) if denom > 1e-9 else 0.0,
        }

        composite_36 += COMPOSITE_WEIGHTS[disease] * attributed

    composite = _group_to_base(composite_36)

    composite_xgb = sum(
        COMPOSITE_WEIGHTS[d] * per_disease[d]["xgb_component"] for d in DISEASES
    )
    composite_transformer = sum(
        COMPOSITE_WEIGHTS[d] * per_disease[d]["transformer_component"] for d in DISEASES
    )
    composite_denom = abs(composite_xgb) + abs(composite_transformer)

    # Base value: the meta-learner's output when every feature sits at the
    # explainer's expected value, weighted the same way as the composite.
    base_value = sum(
        COMPOSITE_WEIGHTS[d] * DISEASE_SCALE[d]
        * sum(W_x[i, h_idx] * head_base[head] for h_idx, head in enumerate(DISEASES))
        for i, d in enumerate(DISEASES)
    )

    return {
        "composite_contributions": {k: round(v, 3) for k, v in composite.items()},
        "per_disease":             per_disease,
        "base_value":              round(float(base_value), 2),
        "explained_fraction":      (
            round(abs(composite_xgb) / composite_denom, 3) if composite_denom > 1e-9 else 0.0
        ),
        "engineered_detail": {
            name: round(float(v), 4)
            for name, v in zip(XGB_FEATURE_NAMES, composite_36)
        },
    }


def _describe_feature(feat: str, raw_val: Optional[float], shap_val: float) -> str:
    """One human-readable sentence per feature: value, judgement, direction."""
    label     = FEATURE_LABELS.get(feat, feat)
    magnitude = abs(shap_val)

    if magnitude < 0.5:
        impact = "minimal impact"
    elif magnitude < 2.0:
        impact = "moderate impact"
    else:
        impact = "significant impact"

    unit, note = _format_value(feat, raw_val)
    arrow = "↑ risk" if shap_val > 0 else "↓ risk"
    prefix = f"{label} ({unit}" + (f", {note}" if note else "") + ")"
    return f"{prefix} — {arrow} by {magnitude:.2f} pts [{impact}]"


def _format_value(feat: str, v: Optional[float]) -> Tuple[str, str]:
    if v is None:
        return "not recorded", ""
    if feat == "sleep_hours":
        return f"{v:.1f}h/night", "within healthy range" if v >= 7 else "below recommended 7-9h"
    if feat == "steps":
        return f"{int(v):,} steps/day", "meeting activity goals" if v >= 8000 else "below 8,000 step target"
    if feat == "hrv_rmssd":
        return f"{v:.0f} ms RMSSD", "healthy variability" if v >= 40 else "reduced variability"
    if feat == "stress_level":
        return f"{v:.0f}/10", "manageable" if v <= 4 else "elevated"
    if feat == "sugar_intake_g":
        return f"{v:.0f} g/day", "within guideline" if v <= 50 else "above WHO 50 g guideline"
    if feat == "bmi":
        if 18.5 <= v <= 22.9:
            note = "healthy (Asian-Indian range)"
        elif v >= 25:
            note = "obese (Asian-Indian cut-off)"
        elif v >= 23:
            note = "overweight (Asian-Indian cut-off)"
        else:
            note = "underweight"
        return f"{v:.1f}", note
    if feat == "whr":
        return f"{v:.2f}", "elevated central adiposity" if v >= 0.90 else "within range"
    if feat == "age":
        return f"{v:.0f} yrs", "age-related baseline"
    if feat == "gender":
        return ("male" if v >= 0.5 else "female"), ""
    if feat.startswith("fam_"):
        return ("positive" if v >= 0.5 else "negative"), "non-modifiable"
    return f"{v:.2f}", ""


def _split_factors(
    contributions: Dict[str, float],
    raw: Dict[str, Optional[float]],
) -> Tuple[List[Dict], List[Dict]]:
    """Split into risk-increasing and protective, each sorted by magnitude."""
    drivers, protective = [], []
    for feat, val in contributions.items():
        entry = {
            "feature":     feat,
            "label":       FEATURE_LABELS.get(feat, feat),
            "shap_value":  round(val, 3),
            "value":       raw.get(feat),
            "modifiable":  feat not in NON_MODIFIABLE,
        }
        (drivers if val > 0 else protective).append(entry)

    drivers.sort(key=lambda x: -x["shap_value"])
    protective.sort(key=lambda x: x["shap_value"])
    return drivers, protective


async def explain_risk(
    user_id: str,
    log_id: str,
    normalized: dict,
    risk_score: float,
) -> Dict[str, Any]:
    """
    Explains the score that compute_risk() actually produced.

    Reads the exact snapshot risk_service persisted to risk_scores.raw_features
    rather than re-deriving it from `normalized`, so the explanation is
    guaranteed to describe the same model input that produced the number. The
    old implementation denormalized independently and could drift.
    """
    pool = get_db()

    async with pool.acquire() as conn:
        risk_row = await conn.fetchrow(
            """
            SELECT raw_features
            FROM risk_scores
            WHERE user_id = $1 AND log_id = $2
            ORDER BY timestamp DESC LIMIT 1
            """,
            user_id, log_id,
        )

        user = await conn.fetchrow(
            "SELECT age FROM users WHERE user_id = $1", user_id,
        )

        # Same history window risk_service uses (one row per calendar day, not
        # per submission — see the identical query there for why), so the
        # sequence this explains matches the sequence that produced the score.
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

    snapshot = _pj(risk_row["raw_features"], {}) if risk_row else {}
    age = float(snapshot.get("age") or (user["age"] if user and user["age"] else 35))

    if not snapshot:
        # No persisted snapshot (explain called before compute_risk) — rebuild
        # from normalized as a last resort.
        snapshot = _denorm_fallback(normalized)
        snapshot["age"] = age

    history = [_merge_extras(dict(r)) for r in history_rows]

    if history:
        sequence, n_real = build_sequence_from_history(history, snapshot, age)
    else:
        sequence, n_real = build_sequence_from_snapshot(snapshot, age), 0

    # SHAP over 3 tree ensembles is CPU-bound — keep it off the event loop.
    explained = await asyncio.to_thread(_explain_sequence, sequence)

    contributions = explained["composite_contributions"]

    # Raw values for display, read off the day we're explaining (the last one)
    today = sequence[-1]
    raw_display = {feat: today.get(feat) for feat in FEATURE_LABELS}

    risk_drivers, protective = _split_factors(contributions, raw_display)
    descriptions = {
        feat: _describe_feature(feat, raw_display.get(feat), contributions.get(feat, 0.0))
        for feat in contributions
    }

    modifiable_drivers = [d for d in risk_drivers if d["modifiable"]]
    primary_driver = (
        modifiable_drivers[0]["feature"] if modifiable_drivers
        else (risk_drivers[0]["feature"] if risk_drivers else "stress_level")
    )

    # Legacy-shaped view so /insights and the existing frontend keep working
    legacy = {}
    for icmr, legacy_key in ICMR_TO_LEGACY.items():
        if icmr in contributions:
            legacy[legacy_key] = round(contributions[icmr], 3)

    result = {
        "shap_contributions":  legacy,
        "icmr_contributions":  contributions,
        "per_disease":         explained["per_disease"],
        "risk_drivers":        risk_drivers,
        "protective_factors":  protective,
        "descriptions":        descriptions,
        "primary_driver":      primary_driver,
        "base_value":          explained["base_value"],
        "engineered_detail":   explained["engineered_detail"],
        # Provenance — what SHAP does and does not cover
        "explains":            "XGBoost specialist heads (Transformer share not SHAP-attributable)",
        "explained_fraction":  explained["explained_fraction"],
        "method":              "shap.TreeExplainer over 3 XGBoost specialists, meta-weighted",
        "n_real_days":         n_real,
        "sequence_source":     "history" if n_real > 1 else "snapshot_tiled",
    }

    await _persist(pool, user_id, log_id, risk_score, result, legacy, primary_driver)
    return result


async def _persist(
    pool, user_id: str, log_id: str, risk_score: float,
    result: dict, legacy: dict, primary_driver: str,
) -> None:
    async with pool.acquire() as conn:
        # Merge onto the existing risk_scores row without clobbering the
        # disease scores compute_risk() wrote there.
        existing_row = await conn.fetchrow(
            "SELECT shap_contributions FROM risk_scores WHERE user_id = $1 AND log_id = $2",
            user_id, log_id,
        )
        existing = _pj(existing_row["shap_contributions"], {}) if existing_row else {}

        merged = {**legacy, **{
            k: v for k, v in existing.items()
            if k in ("diabetes_risk", "cvd_risk", "hypertension_risk")
        }}

        await conn.execute(
            """
            UPDATE risk_scores
            SET shap_contributions = $1, primary_cause = $2
            WHERE user_id = $3 AND log_id = $4
            """,
            json.dumps(merged), primary_driver, user_id, log_id,
        )

        await conn.execute(
            """
            INSERT INTO explanations (
                user_id, log_id, risk_score, base_value,
                shap_contributions, risk_drivers, protective_factors,
                descriptions, primary_driver, timestamp
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            user_id, log_id, risk_score, result["base_value"],
            # Store the full ICMR + per-disease detail, not just the legacy 6
            json.dumps({
                "icmr":        result["icmr_contributions"],
                "legacy":      legacy,
                "per_disease": result["per_disease"],
                "explains":    result["explains"],
                "explained_fraction": result["explained_fraction"],
            }),
            json.dumps(result["risk_drivers"]),
            json.dumps(result["protective_factors"]),
            json.dumps(result["descriptions"]),
            primary_driver,
            datetime.now(timezone.utc),
        )


def _merge_extras(row: dict) -> dict:
    """Lift wearable-measured values out of the extras JSONB onto the row."""
    extras = _pj(row.pop("extras", None), {}) or {}
    for key in ("hrv_rmssd", "sugar_intake_g"):
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


def _denorm_fallback(normalized: dict) -> dict:
    """Reconstruct a raw snapshot from normalized [0,1] values."""
    return {
        field: round(lo + normalized.get(field, 0.5) * (hi - lo), 2)
        for field, (lo, hi) in _DENORM_BOUNDS.items()
    }
