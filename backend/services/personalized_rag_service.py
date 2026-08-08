"""
Personalized RAG orchestration — combines two DELIBERATELY SEPARATE retrieval
sources into one answer, without rebuilding either:

  1. STATIC clinical-guideline knowledge — reuses `rag.py` (ClinicalRAG)
     unmodified. Structure-aware chunking, TF-IDF retrieval, clinical
     synonym expansion. This answers "what does the guideline say" —
     population-level, evidence-based, the same for every user.

  2. PERSONAL health memory — reuses `memory_service.py` (mem0/pgvector),
     now actually populated: `store_health_observation()` runs on every
     completed check-in via `run_full_pipeline` (backend/routes/health_data.py),
     Garmin-sourced data included, since it fires regardless of source. This
     answers "what does THIS user's own data show."

WHY NOT ONE MERGED RETRIEVAL INDEX
-----------------------------------
These are semantically different kinds of "context" and conflating them
would blur exactly the distinction that matters most in a health app: a
generic guideline statement ("the ADA recommends 150 min/week of activity")
must never be presented with the same confidence as a fact about this
specific patient ("your steps have averaged 890/day for 5 days"). Both
retrievers stay separate; the two context blocks are labelled separately
in the prompt this feeds (see chat_service.py), and the LLM is instructed
to keep that distinction explicit in its answer.

WHY NOT A SECOND GENERATION CALL
----------------------------------
rag.py's own ClinicalRAG.query() does retrieval AND generation in one call
via its own GroqGenerator. Calling that here as well as chat_service's own
Groq call would mean two sequential LLM round-trips per chat message (extra
latency) with two different "voices" stitched together. Instead this module
does retrieval only — chat_service.py's existing single system prompt
absorbs the guideline context alongside everything else it already
assembles, and answers once, consistently.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_rag_instance = None
_rag_load_attempted = False


def _get_rag():
    """
    Lazy singleton, loaded once. If the guideline corpus directory doesn't
    exist (it doesn't, as shipped — see the RAG_CORPUS_DIR note in the
    project handoff), ClinicalRAG initializes with is_ready=False rather than
    raising, and every retrieval call below returns an empty list. Nothing
    downstream needs to special-case "corpus missing" — it just gets no
    guideline context, same as "no chunks matched."
    """
    global _rag_instance, _rag_load_attempted
    if _rag_load_attempted:
        return _rag_instance
    _rag_load_attempted = True

    try:
        from rag import ClinicalRAG
        from backend.config import settings

        _rag_instance = ClinicalRAG(
            corpus_dir=settings.rag_corpus_dir,
            groq_api_key=settings.groq_api_key,
        )
        if _rag_instance.is_ready:
            logger.info(f"[personalized_rag] guideline corpus loaded: {_rag_instance.stats()}")
        else:
            logger.warning(
                f"[personalized_rag] guideline corpus not loaded (dir="
                f"'{settings.rag_corpus_dir}') — chat will run without "
                "clinical-guideline context until real documents are added."
            )
    except Exception as e:
        logger.error(f"[personalized_rag] failed to initialize ClinicalRAG: {e}")
        _rag_instance = None

    return _rag_instance


def is_guideline_corpus_loaded() -> bool:
    rag = _get_rag()
    return bool(rag and rag.is_ready)


def get_guideline_chunks(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """Raw retrieval, for callers that want the chunk metadata directly."""
    rag = _get_rag()
    if not rag or not rag.is_ready:
        return []
    try:
        return rag.retrieve_only(query)[:top_k]
    except Exception as e:
        logger.warning(f"[personalized_rag] guideline retrieval failed: {e}")
        return []


def format_guideline_context(query: str, top_k: int = 4) -> Optional[str]:
    """
    Formatted, citation-ready text block for prompt injection, or None when
    there's nothing to show (corpus not loaded, or no chunk cleared the
    relevance threshold). Mirrors the chunk_type/section labelling rag.py
    already computes — reused, not reinvented.
    """
    chunks = get_guideline_chunks(query, top_k=top_k)
    if not chunks:
        return None

    lines = ["═══ CLINICAL GUIDELINE CONTEXT (general population evidence, not this patient's data) ═══"]
    for i, c in enumerate(chunks, 1):
        source = c.get("source", "guideline").replace("_", " ").title()
        section = " > ".join(c.get("section_path", []) or [])
        chunk_type = c.get("chunk_type", "general").upper()
        loc = f" | {section}" if section else ""
        lines.append(f"[G{i}] {source}{loc} | {chunk_type}")
        lines.append(f"    {c['text'][:400]}")

    return "\n".join(lines)


async def get_personalized_context(user_id: str, query: str) -> Dict[str, Any]:
    """
    Fetches both retrieval sources for one query. Kept async (even though
    guideline retrieval is sync/TF-IDF, i.e. fast) so callers in chat_service
    can gather this alongside other async lookups without blocking the loop
    on the mem0 search.
    """
    from backend.services.memory_service import get_user_context

    guideline_text = format_guideline_context(query)
    mem_ctx = await get_user_context(user_id, query=query, limit=6)

    return {
        "guideline_context": guideline_text,
        "guideline_corpus_loaded": is_guideline_corpus_loaded(),
        "personal_memories": [m.get("text", "") for m in mem_ctx.get("memories", []) if m.get("text")],
        "personal_memory_source": mem_ctx.get("source"),  # "mem0" | "fallback"
    }
