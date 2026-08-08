"""
Environmental context endpoints (Block C).

These return air quality as an ADVISORY shown next to the CVD score. Nothing
here feeds the risk model — see the module docstring in air_quality_service.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.services import air_quality_service

router = APIRouter()


@router.get("/environment/air-quality")
async def air_quality(
    city: Optional[str] = None,
    user_id: Optional[str] = None,
    force_refresh: bool = False,
):
    """
    PM2.5, CPCB AQI, and the cited cardiovascular advisory for a city.
    Always succeeds: degrades to a labelled bundled baseline if OpenAQ is
    unreachable or unkeyed.
    """
    try:
        return await air_quality_service.get_air_quality(
            city=city, user_id=user_id, force_refresh=force_refresh,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Air-quality lookup failed: {type(e).__name__}")


@router.get("/environment/cvd-advisory")
async def cvd_advisory(user_id: str, city: Optional[str] = None):
    """
    The user's model-derived CVD score and the environmental advisory as two
    separate, explicitly uncombined figures.
    """
    try:
        return await air_quality_service.cvd_context(user_id, city)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Advisory lookup failed: {type(e).__name__}")
