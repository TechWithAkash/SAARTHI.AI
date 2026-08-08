import json

from fastapi import APIRouter, HTTPException

from backend.db.postgres import get_db
from backend.models.health import (
    SimulationResponse,
    SimulationScenarios,
    WhatIfRequest,
    WhatIfResponse,
)
from backend.services.simulation_service import run_whatif

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


@router.get("/simulate", response_model=SimulationResponse)
async def get_simulation(user_id: str):
    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM simulations WHERE user_id=$1 ORDER BY generated_at DESC LIMIT 1",
            user_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="No simulation found for user")

    scenarios = _pj(row["scenarios"], {}) or {}

    # by_disease is nested inside scenarios; pull it out so the composite
    # trajectories still validate against SimulationScenarios.
    by_disease = scenarios.pop("by_disease", None)

    missing = [k for k in ("current", "improved", "optimal") if k not in scenarios]
    if missing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Stored simulation is missing {', '.join(missing)} — it predates the "
                "ensemble migration. Submit a new check-in to regenerate."
            ),
        )

    return SimulationResponse(
        user_id=user_id,
        scenarios=SimulationScenarios(
            current=scenarios["current"],
            improved=scenarios["improved"],
            optimal=scenarios["optimal"],
        ),
        timeline_days=_pj(row["timeline_days"], []) or [],
        projected_risk_reduction=_pj(row["projected_risk_reduction"], {}) or {},
        by_disease=by_disease,
        scenario_assumptions=_pj(row["scenario_assumptions"], {}) or {},
    )


@router.post("/simulate/whatif", response_model=WhatIfResponse)
async def post_whatif(req: WhatIfRequest):
    """
    Interactive counterfactual scoring.

    "If I slept 8h and walked 12,000 steps, what happens to my risk?" — scores
    the user's current state and the modified state through the same ensemble
    and returns both plus per-disease deltas. Roughly 5 ms of model time, so
    it's safe to call on slider drag (debounced).
    """
    overrides = req.overrides()
    if not overrides:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one metric to change (sleep, steps, stress_level, diet_score, heart_rate, bmi).",
        )

    try:
        return WhatIfResponse(**await run_whatif(req.user_id, overrides))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
