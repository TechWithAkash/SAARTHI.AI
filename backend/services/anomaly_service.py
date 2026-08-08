"""
Anomaly Detection Service — DarpanAI Phase 7.

Three-layer detection stack (all layers run, results merged):

  Layer 1 — Rule-based bounds  (always active, zero-latency)
             Hard clinical limits that are always abnormal regardless of history.

  Layer 2 — Personal z-score   (active when >= 5 prior readings exist)
             Compares new reading to the user's own historical mean ± std.
             Threshold: |z| > 2.5σ  (flags top ~1.2% of personal distribution)

  Layer 3 — Merlion IsolationForest  (active when >= 30 prior readings exist)
             Unsupervised anomaly scoring on the full feature vector.
             Falls back to sklearn IsolationForest if Merlion not installed.

Severity mapping:
  critical  — rule-based hard limit exceeded (e.g. HR > 160)
  high      — |z| > 4σ  OR  Merlion score > 0.7
  medium    — |z| > 3σ  OR  Merlion score > 0.5
  low       — |z| > 2.5σ
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import numpy as np

from backend.db.postgres import get_db

# ── Constants ────────────────────────────────────────────────────────────────

METRICS = ["heart_rate", "steps", "sleep", "stress_level", "bmi", "diet_score"]

# Hard clinical bounds (always anomalous regardless of baseline)
HARD_BOUNDS: Dict[str, Dict] = {
    "heart_rate":   {"min": 40,  "max": 160, "severity": "critical"},
    "blood_oxygen": {"min": 90,  "max": 100, "severity": "critical"},
    "systolic_bp":  {"min": 80,  "max": 180, "severity": "high"},
    "diastolic_bp": {"min": 50,  "max": 110, "severity": "high"},
    "sleep":        {"min": 2,   "max": 14,  "severity": "high"},
    "bmi":          {"min": 14,  "max": 50,  "severity": "medium"},
    "steps":        {"min": 0,   "max": 50000, "severity": "low"},
}

Z_THRESHOLDS = [
    (4.0, "high"),
    (3.0, "medium"),
    (2.5, "low"),
]

MIN_HISTORY_ZSCORE   = 5
MIN_HISTORY_MERLION  = 30

# ── Merlion / fallback ────────────────────────────────────────────────────────

def _try_isolation_forest_score(history_matrix: np.ndarray, new_vector: np.ndarray) -> Optional[float]:
    """
    Fits sklearn IsolationForest on history, scores the new point.
    Returns anomaly score in [0,1] — higher = more anomalous.
    Merlion's IsolationForest wraps sklearn under the hood; we use sklearn
    directly here because Merlion's `get_anomaly_score` requires contiguous
    timestamps and cannot score a single out-of-sample point.
    """
    try:
        from sklearn.ensemble import IsolationForest as SkIsoForest
        clf = SkIsoForest(n_estimators=100, contamination=0.05, random_state=42)
        clf.fit(history_matrix)
        # score_samples returns negative log-likelihood: more negative = more anomalous
        raw = clf.score_samples(new_vector.reshape(1, -1))[0]
        # Normalise to [0,1]: typical range is [-0.7, -0.3]; invert so 1 = very anomalous
        normalised = float(np.clip((raw + 0.7) / 0.4, 0.0, 1.0))
        return 1.0 - normalised
    except Exception:
        return None


def _merlion_severity(score: float) -> Optional[str]:
    if score > 0.7:
        return "high"
    if score > 0.5:
        return "medium"
    return None


# ── Layer helpers ─────────────────────────────────────────────────────────────

def _rule_based(raw: dict) -> List[Dict]:
    anomalies = []
    for metric, bounds in HARD_BOUNDS.items():
        val = raw.get(metric)
        if val is None:
            continue
        lo, hi = bounds["min"], bounds["max"]
        if val < lo or val > hi:
            expected_range = {"min": lo, "max": hi}
            deviation_pct  = round(
                abs(val - (lo if val < lo else hi)) / (hi - lo) * 100, 1
            )
            anomalies.append({
                "metric":         metric,
                "observed_value": val,
                "expected_range": expected_range,
                "deviation_pct":  deviation_pct,
                "severity":       bounds["severity"],
                "layer":          "rule",
                "message":        (
                    f"{metric.replace('_',' ').title()} of {val} is outside "
                    f"safe range [{lo}–{hi}]"
                ),
            })
    return anomalies


def _zscore_based(raw: dict, history: List[dict]) -> List[Dict]:
    if len(history) < MIN_HISTORY_ZSCORE:
        return []

    anomalies = []
    for metric in METRICS:
        val = raw.get(metric)
        if val is None:
            continue
        hist_vals = [h[metric] for h in history if metric in h and h[metric] is not None]
        if len(hist_vals) < MIN_HISTORY_ZSCORE:
            continue

        mean = np.mean(hist_vals)
        std  = np.std(hist_vals)
        if std < 1e-6:
            continue

        z = abs((val - mean) / std)
        severity = None
        for threshold, sev in Z_THRESHOLDS:
            if z >= threshold:
                severity = sev
                break

        if severity:
            deviation_pct = round((z / 2.5) * 100, 1)
            anomalies.append({
                "metric":         metric,
                "observed_value": val,
                "expected_range": {
                    "min": round(mean - 2.5 * std, 2),
                    "max": round(mean + 2.5 * std, 2),
                },
                "deviation_pct": deviation_pct,
                "z_score":       round(z, 2),
                "severity":      severity,
                "layer":         "zscore",
                "message":       (
                    f"{metric.replace('_',' ').title()} is {z:.1f}σ from your "
                    f"personal baseline (mean={mean:.1f})"
                ),
            })
    return anomalies


def _isolation_forest_based(raw: dict, history: List[dict]) -> List[Dict]:
    if len(history) < MIN_HISTORY_MERLION:
        return []

    feature_keys = METRICS
    history_matrix = np.array([
        [h.get(k, 0.0) for k in feature_keys]
        for h in history
        if all(k in h for k in feature_keys)
    ])
    if len(history_matrix) < MIN_HISTORY_MERLION:
        return []

    new_vector = np.array([raw.get(k, 0.0) for k in feature_keys])
    score = _try_isolation_forest_score(history_matrix, new_vector)
    if score is None:
        return []

    severity = _merlion_severity(score)
    if not severity:
        return []

    return [{
        "metric":         "composite",
        "observed_value": round(score, 3),
        "expected_range": {"min": 0.0, "max": 0.5},
        "deviation_pct":  round(score * 100, 1),
        "severity":       severity,
        "layer":          "isolation_forest",
        "message":        (
            f"Your overall health pattern is unusual today "
            f"(anomaly score: {score:.2f}/1.0)"
        ),
    }]


def _merge_anomalies(
    rule: List[Dict],
    zscore: List[Dict],
    isoforest: List[Dict],
) -> List[Dict]:
    """Merge, deduplicate by metric, keep highest severity."""
    SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    merged: Dict[str, Dict] = {}

    for a in rule + zscore + isoforest:
        metric = a["metric"]
        if metric not in merged:
            merged[metric] = a
        else:
            # COR-5: an unrecognised severity string used to KeyError here and
            # kill the whole anomaly pipeline for every metric, not just the
            # offending one. .get(..., 0) treats an unknown severity as lowest
            # rank instead of crashing.
            if SEVERITY_RANK.get(a["severity"], 0) > SEVERITY_RANK.get(merged[metric]["severity"], 0):
                merged[metric] = a

    return sorted(merged.values(), key=lambda x: -SEVERITY_RANK.get(x["severity"], 0))


# ── Public API ────────────────────────────────────────────────────────────────

async def detect_anomalies(
    user_id: str,
    log_id: str,
    raw: dict,
) -> List[Dict[str, Any]]:
    pool = get_db()

    async with pool.acquire() as conn:
        # Fetch recent history (last 90 readings) — flat columns, no nested subdocs
        rows = await conn.fetch(
            """
            SELECT heart_rate, steps, sleep, bmi, stress_level, diet_score,
                   systolic_bp, diastolic_bp, blood_oxygen
            FROM health_logs
            WHERE user_id = $1
            ORDER BY timestamp DESC
            LIMIT 90
            """,
            user_id,
        )

        # Each asyncpg.Record is accessed like a dict — build plain dicts for numpy
        history = [dict(row) for row in rows]

        rule_anomalies      = _rule_based(raw)
        zscore_anomalies    = _zscore_based(raw, history)
        isoforest_anomalies = _isolation_forest_based(raw, history)

        final = _merge_anomalies(rule_anomalies, zscore_anomalies, isoforest_anomalies)

        # Persist each anomaly as a separate row
        now = datetime.now(timezone.utc)
        for anomaly in final:
            await conn.execute(
                """
                INSERT INTO anomalies (
                    user_id, log_id, metric, observed_value, expected_range,
                    deviation_pct, z_score, severity, layer, message,
                    acknowledged, detected_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9, $10,
                    $11, $12
                )
                """,
                user_id,
                log_id,
                anomaly["metric"],
                float(anomaly["observed_value"]),
                json.dumps(anomaly["expected_range"]),       # JSONB → string
                anomaly.get("deviation_pct"),
                anomaly.get("z_score"),
                anomaly["severity"],
                anomaly["layer"],
                anomaly["message"],
                False,
                now,
            )

    return final
