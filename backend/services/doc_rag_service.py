"""
DarpanAI — Document RAG Service
================================
Handles document ingestion and retrieval for the /chat endpoint.

Supported formats:
  - PDF (text-layer via pdfplumber; tables + paragraphs)
  - Plain text / Markdown
  - Images (basic OCR via pytesseract if installed; falls back to Groq vision)

Architecture (zero extra infra):
  - Text extracted → split into overlapping chunks
  - TF-IDF vectors computed in-process (scikit-learn, already installed)
  - Cosine similarity for retrieval (top-k chunks)
  - Sessions stored in-memory with TTL of 2 hours
  - Each session keyed by a UUID returned to the frontend

Usage:
    from backend.services.doc_rag_service import ingest_document, retrieve_context

    session_id = await ingest_document(file_bytes, filename, user_id)
    context    = retrieve_context(session_id, query, top_k=3)
"""

import io
import re
import time
import uuid
import logging
from typing import Optional
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ── In-memory session store ───────────────────────────────────────────────────
# { session_id: { "chunks": [...], "vectorizer": ..., "matrix": ...,
#                 "filename": str, "user_id": str, "created_at": float } }
_DOC_SESSIONS: dict = {}
_SESSION_TTL_SECONDS = 7200  # 2 hours


# ── Text extraction ───────────────────────────────────────────────────────────

def _extract_pdf(data: bytes) -> str:
    """Extract text from a PDF using pdfplumber (handles tables + paragraphs)."""
    try:
        import pdfplumber
    except ImportError as e:
        # Previously this ImportError bubbled up as an opaque HTTP 500
        # ("Processing failed") from chat.py's generic handler. Name the real
        # cause so it's fixable in one look instead of a support ticket.
        raise RuntimeError(
            "PDF support requires the 'pdfplumber' package, which is not "
            "installed in this environment. Run: pip install pdfplumber"
        ) from e

    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for i, page in enumerate(pdf.pages):
            # Extract tables first (medical labs are often tabular)
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    clean = [str(c).strip() if c else "" for c in row]
                    if any(clean):
                        text_parts.append(" | ".join(clean))

            # Extract remaining text
            txt = page.extract_text()
            if txt:
                text_parts.append(txt)

    return "\n".join(text_parts)


def _extract_image(data: bytes, filename: str) -> str:
    """Try pytesseract OCR; if unavailable, return a placeholder."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img)
    except ImportError:
        logger.warning("[doc_rag] pytesseract not installed — image OCR unavailable")
        return f"[Image file: {filename} — install pytesseract + tesseract for OCR support]"
    except Exception as e:
        logger.warning(f"[doc_rag] OCR failed: {e}")
        return f"[Could not OCR image: {filename}]"


def _extract_text(data: bytes, filename: str) -> str:
    """Route to the correct extractor based on file extension."""
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(data)

    if ext in (".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"):
        return _extract_image(data, filename)

    # Plain text / Markdown / CSV / HTML — decode best-effort
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue

    return data.decode("utf-8", errors="replace")


# ── Chunking ──────────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    """
    Split text into overlapping chunks suitable for RAG retrieval.
    Uses sentence-aware splitting so medical values aren't split mid-sentence.
    """
    # Normalise whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # Split on sentence boundaries (period + space or newline)
    sentences = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sent in sentences:
        sent_len = len(sent)
        if current_len + sent_len > chunk_size and current:
            chunks.append(" ".join(current))
            # Overlap: keep last few sentences for context continuity
            overlap_sents: list[str] = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s) < overlap:
                    overlap_sents.insert(0, s)
                    overlap_len += len(s)
                else:
                    break
            current = overlap_sents
            current_len = overlap_len

        current.append(sent)
        current_len += sent_len

    if current:
        chunks.append(" ".join(current))

    return [c for c in chunks if len(c) > 30]  # drop empty/trivial chunks


# ── TF-IDF index ─────────────────────────────────────────────────────────────

def _build_index(chunks: list[str]):
    """Build a TF-IDF matrix over the chunks for fast cosine similarity lookup."""
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words="english",
        max_features=8000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(chunks)
    return vectorizer, matrix


# ── Public API ────────────────────────────────────────────────────────────────

async def ingest_document(
    file_bytes: bytes,
    filename: str,
    user_id: str,
) -> dict:
    """
    Ingest a document and return a session dict:
      { session_id, filename, chunk_count, preview }

    Raises ValueError if the document yields no usable text.
    """
    # Prune expired sessions
    _prune_sessions()

    text = _extract_text(file_bytes, filename)

    if not text or len(text.strip()) < 50:
        raise ValueError(f"Could not extract meaningful text from {filename}. "
                         "Ensure the PDF has a text layer (not a scanned image without OCR).")

    chunks = _chunk_text(text)
    if not chunks:
        raise ValueError("Document contained no parseable chunks.")

    vectorizer, matrix = _build_index(chunks)

    session_id = str(uuid.uuid4())
    _DOC_SESSIONS[session_id] = {
        "chunks":     chunks,
        "vectorizer": vectorizer,
        "matrix":     matrix,
        "filename":   filename,
        "user_id":    user_id,
        "full_text":  text[:2000],       # preview for system prompt header
        "created_at": time.time(),
    }

    logger.info(f"[doc_rag] session={session_id} file={filename} chunks={len(chunks)}")

    return {
        "session_id":  session_id,
        "filename":    filename,
        "chunk_count": len(chunks),
        "preview":     text[:300].replace("\n", " ").strip(),
    }


def retrieve_context(session_id: str, query: str, top_k: int = 4) -> Optional[str]:
    """
    Retrieve the top-k most relevant chunks for the given query.
    Returns a formatted string ready for injection into the system prompt,
    or None if the session doesn't exist.
    """
    session = _DOC_SESSIONS.get(session_id)
    if not session:
        return None

    vectorizer: TfidfVectorizer = session["vectorizer"]
    matrix = session["matrix"]
    chunks: list[str] = session["chunks"]
    filename: str = session["filename"]

    try:
        q_vec = vectorizer.transform([query])
        scores = cosine_similarity(q_vec, matrix).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        relevant = [chunks[i] for i in top_indices if scores[i] > 0.05]
        if not relevant:
            # Fall back to first few chunks (document preamble often has patient info)
            relevant = chunks[:3]

        context_block = "\n\n---\n\n".join(relevant)
        return (
            f"═══ UPLOADED MEDICAL DOCUMENT: {filename} ═══\n"
            f"The following are the most relevant excerpts from the patient's uploaded document:\n\n"
            f"{context_block}\n\n"
            f"Answer the user's question using this document as primary evidence. "
            f"Quote specific values (e.g. HbA1c: 7.2%, Glucose: 126 mg/dL) when present. "
            f"Relate findings to the patient's existing risk profile when relevant."
        )
    except Exception as e:
        logger.error(f"[doc_rag] retrieval error: {e}")
        return None


def get_session_info(session_id: str) -> Optional[dict]:
    """Return metadata about a session (filename, chunk_count)."""
    s = _DOC_SESSIONS.get(session_id)
    if not s:
        return None
    return {
        "session_id":  session_id,
        "filename":    s["filename"],
        "chunk_count": len(s["chunks"]),
        "age_minutes": round((time.time() - s["created_at"]) / 60, 1),
    }


def clear_session(session_id: str) -> bool:
    """Explicitly clear a document session (e.g. user clicks 'Remove document')."""
    if session_id in _DOC_SESSIONS:
        del _DOC_SESSIONS[session_id]
        return True
    return False


def _prune_sessions():
    """Remove sessions older than TTL to prevent memory leaks."""
    now = time.time()
    expired = [k for k, v in _DOC_SESSIONS.items() if now - v["created_at"] > _SESSION_TTL_SECONDS]
    for k in expired:
        del _DOC_SESSIONS[k]
    if expired:
        logger.info(f"[doc_rag] pruned {len(expired)} expired sessions")
