import json

from fastapi import APIRouter, HTTPException

from backend.db.postgres import get_db
from backend.models.health import InsightsResponse, SHAPContributions

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


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(user_id: str):
    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM risk_scores WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1",
            user_id,
        )
        # The full explanation (per-disease, ICMR-level, provenance) lives in
        # `explanations`; risk_scores only carries the flattened legacy view.
        expl = await conn.fetchrow(
            "SELECT * FROM explanations WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1",
            user_id,
        )

    if not row:
        raise HTTPException(status_code=404, detail="No insights found for user")

    shap = _pj(row["shap_contributions"], {}) or {}
    detail = _pj(expl["shap_contributions"], {}) if expl else {}

    return InsightsResponse(
        user_id=user_id,
        shap_contributions=SHAPContributions(
            heart_rate=shap.get("heart_rate", 0.0),
            steps=shap.get("steps", 0.0),
            sleep=shap.get("sleep", 0.0),
            stress_level=shap.get("stress_level", 0.0),
            diet_score=shap.get("diet_score", 0.0),
            bmi=shap.get("bmi", 0.0),
            age=shap.get("age", 0.0),
        ),
        causal_chain=row["causal_chain"] or "",
        primary_cause=row["primary_cause"] or "",
        explains=detail.get("explains"),
        explained_fraction=detail.get("explained_fraction"),
        per_disease=detail.get("per_disease"),
        icmr_contributions=detail.get("icmr"),
    )
