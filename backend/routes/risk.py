import json
from typing import List
from fastapi import APIRouter, HTTPException
from backend.db.postgres import get_db
from backend.models.health import RiskResponse

router = APIRouter()


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


def _to_response(user_id: str, row) -> RiskResponse:
    top_risk_factors = _pj(row["top_risk_factors"], [])
    shap_raw = _pj(row["shap_contributions"], {})
    # Saturation flags travel in raw_features (see risk_service.compute_risk) —
    # no schema migration needed since it's already a JSONB scratch bag.
    raw_features = _pj(row["raw_features"], {})

    return RiskResponse(
        user_id=user_id,
        risk_score=row["risk_score"],
        risk_category=row["risk_category"],
        timestamp=row["timestamp"],
        top_risk_factors=top_risk_factors,
        diabetes_risk=shap_raw.get("diabetes_risk"),
        cvd_risk=shap_raw.get("cvd_risk"),
        hypertension_risk=shap_raw.get("hypertension_risk"),
        model_saturated=raw_features.get("model_saturated"),
        saturated_after_fallback=raw_features.get("saturated_after_fallback"),
    )


@router.get("/risk", response_model=RiskResponse)
async def get_risk(user_id: str):
    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM risk_scores WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1",
            user_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="No risk data found for user")
    return _to_response(user_id, row)


@router.get("/risk/history", response_model=List[RiskResponse])
async def get_risk_history(user_id: str):
    pool = get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM risk_scores WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 30",
            user_id,
        )
    return [_to_response(user_id, row) for row in rows]
