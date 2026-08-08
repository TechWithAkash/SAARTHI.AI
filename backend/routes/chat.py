from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from backend.services.chat_service import stream_chat
from backend.services.doc_rag_service import ingest_document, clear_session, get_session_info

router = APIRouter()

MAX_FILE_SIZE_MB = 20


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    user_id: str
    message: str
    history: Optional[List[HistoryMessage]] = []
    doc_session_id: Optional[str] = None   # set when a document is loaded


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming SSE chat endpoint.
    POST body: { user_id, message, history, doc_session_id? }
    Streams tokens word-by-word, then emits a final 'done' event with chips.
    When doc_session_id is present, top-4 relevant chunks are injected as context.
    """
    history = [{"role": m.role, "content": m.content} for m in (request.history or [])]

    return StreamingResponse(
        stream_chat(
            request.user_id,
            request.message,
            history,
            doc_session_id=request.doc_session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/chat/upload")
async def chat_upload_document(
    user_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload a medical document (PDF, image, text) for RAG-based Q&A.
    Returns a session_id that must be included in subsequent /chat/stream requests.

    Supported: .pdf  .txt  .md  .png  .jpg  .jpeg  .webp
    Max size:  20 MB
    """
    # File size guard
    raw = await file.read()
    size_mb = len(raw) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum is {MAX_FILE_SIZE_MB} MB.",
        )

    allowed = {".pdf", ".txt", ".md", ".csv", ".png", ".jpg", ".jpeg", ".webp", ".tiff"}
    from pathlib import Path
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed)}",
        )

    try:
        result = await ingest_document(raw, file.filename or "document", user_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

    return result


@router.delete("/chat/upload/{session_id}")
async def chat_clear_document(session_id: str):
    """Remove a document session from memory."""
    ok = clear_session(session_id)
    return {"cleared": ok, "session_id": session_id}


@router.get("/chat/upload/{session_id}")
async def chat_document_info(session_id: str):
    """Get metadata about a loaded document session."""
    info = get_session_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return info
