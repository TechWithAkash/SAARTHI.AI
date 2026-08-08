from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.services.arena_service import stream_arena_battle
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/arena/stream")
async def get_arena_stream(query: str, user_id: str):
    """
    SSE stream for the Model Arena.
    Runs 3 LLMs concurrently and streams their chunks.
    Then executes a Nano-model evaluation.
    """
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    return StreamingResponse(
        stream_arena_battle(query, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
