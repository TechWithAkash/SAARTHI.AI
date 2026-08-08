"""
Garmin Connect endpoints (BP-6).

/garmin/status is deliberately always safe to call — it reports "not
configured" cleanly rather than erroring, because that is the state the app
sits in until real credentials are present, and the UI needs to render it.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services import garmin_service
from backend.services.garmin_service import GarminUnavailable

router = APIRouter()


class GarminSyncRequest(BaseModel):
    user_id: str
    days: int = Field(default=14, ge=1, le=90, description="Days of history to backfill")


@router.get("/garmin/status")
async def garmin_status(user_id: Optional[str] = None):
    """Connection state, token cache state, and last sync. Never returns credentials."""
    return await garmin_service.status(user_id)


@router.get("/garmin/preview")
async def garmin_preview(cdate: str):
    """
    Fetch one date WITHOUT writing to the database — used to verify field
    mapping against a real account before committing rows.
    """
    try:
        core = await garmin_service.fetch_core(cdate)
        extras = await garmin_service.fetch_enhancements(cdate)
    except GarminUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Garmin upstream error: {type(e).__name__}")

    if core["provenance"] == "unavailable" and not extras:
        raise HTTPException(
            status_code=503,
            detail="No live Garmin data and nothing cached for this date.",
        )
    return {**core, "extras": extras}


@router.post("/garmin/sync")
async def garmin_sync(req: GarminSyncRequest):
    """
    Backfills `days` of Garmin history into health_logs.

    Idempotent: re-running replaces each day rather than duplicating it. The
    response states which fields were device-measured vs app-defaulted per day,
    so "which of these numbers are real?" is answerable.
    """
    try:
        result = await garmin_service.backfill(req.user_id, req.days)
    except GarminUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Garmin sync failed: {type(e).__name__}: {e}")

    if result["days_ingested"] == 0:
        raise HTTPException(
            status_code=503,
            detail=(
                "Garmin returned no usable days. "
                f"Status: {result['status']}, source: {result['source']}. "
                "Check /garmin/status."
            ),
        )
    return result
