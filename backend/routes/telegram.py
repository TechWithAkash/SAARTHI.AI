from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.telegram_service import (
    generate_link_token,
    get_status,
    unlink_account,
)

router = APIRouter()


class GenerateTokenRequest(BaseModel):
    user_id: str


class UnlinkRequest(BaseModel):
    user_id: str


@router.post("/telegram/generate-token")
async def generate_token(req: GenerateTokenRequest):
    token = await generate_link_token(req.user_id)
    return {"token": token, "bot": "@darpanAi_bot", "instruction": f"Send '/start {token}' to @darpanAi_bot on Telegram"}


@router.get("/telegram/status")
async def telegram_status(user_id: str):
    return await get_status(user_id)


@router.post("/telegram/unlink")
async def telegram_unlink(req: UnlinkRequest):
    await unlink_account(req.user_id)
    return {"success": True}
