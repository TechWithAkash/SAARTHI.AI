from fastapi import APIRouter, HTTPException
from typing import List, Dict
from backend.services.memory_service import get_all_memories, delete_user_memories

router = APIRouter()


@router.get("/memory/{user_id}")
async def fetch_memories(user_id: str):
    """Fetch all memories stored in mem0 for a user."""
    memories = await get_all_memories(user_id)
    return {"user_id": user_id, "memories": memories}


@router.delete("/memory/{user_id}")
async def wipe_memories(user_id: str):
    """Delete all memories for a user (GDPR/Privacy)."""
    success = await delete_user_memories(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to clear memories")
    return {"status": "success", "message": "All memories cleared"}
