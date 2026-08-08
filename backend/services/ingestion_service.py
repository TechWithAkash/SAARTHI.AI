import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

from backend.db.postgres import get_db
from backend.models.health import HealthDataInput


# Normalization bounds (min, max) per feature
NORM_BOUNDS = {
    "heart_rate":   (40,  200),
    "steps":        (0,   20000),
    "sleep":        (0,   12),
    "bmi":          (15,  50),
    "stress_level": (1,   10),
    "diet_score":   (1,   10),
}


def normalize(value: float, min_val: float, max_val: float) -> float:
    return round(max(0.0, min(1.0, (value - min_val) / (max_val - min_val))), 4)


def build_normalized(data: HealthDataInput) -> Dict[str, float]:
    return {
        field: normalize(getattr(data, field), lo, hi)
        for field, (lo, hi) in NORM_BOUNDS.items()
    }


def compute_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


async def ingest(data: HealthDataInput) -> Dict[str, Any]:
    pool = get_db()
    log_id = f"log_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    normalized = build_normalized(data)

    # Device-measured metrics live in extras so they override the derived
    # proxies (HC-03 HRV, HC-04 sugar) downstream in ensemble_service._icmr_day.
    extras = dict(data.extras or {})
    if data.hrv_rmssd is not None:
        extras["hrv_rmssd"] = data.hrv_rmssd
    if data.sugar_intake_g is not None:
        extras["sugar_intake_g"] = data.sugar_intake_g

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO health_logs (
                log_id, user_id, heart_rate, steps, sleep, bmi,
                stress_level, diet_score, systolic_bp, diastolic_bp,
                blood_oxygen, active_minutes, water_intake_ml, source,
                heart_rate_norm, steps_norm, sleep_norm, bmi_norm,
                stress_level_norm, diet_score_norm, extras, timestamp
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10,
                $11, $12, $13, $14,
                $15, $16, $17, $18,
                $19, $20, $21, $22
            )
            """,
            log_id,
            data.user_id,
            data.heart_rate,
            data.steps,
            data.sleep,
            data.bmi,
            data.stress_level,
            data.diet_score,
            data.systolic_bp,
            data.diastolic_bp,
            data.blood_oxygen,
            data.active_minutes,
            data.water_intake_ml,
            data.source,
            normalized["heart_rate"],
            normalized["steps"],
            normalized["sleep"],
            normalized["bmi"],
            normalized["stress_level"],
            normalized["diet_score"],
            json.dumps(extras),
            now,
        )

    return {
        "log_id": log_id,
        "timestamp": now,
        "normalized": normalized,
        "raw": data.model_dump(),
        "extras": extras,
    }
