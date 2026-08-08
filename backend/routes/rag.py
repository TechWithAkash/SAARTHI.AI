"""
RAG status endpoint — read-only, no side effects. Exists so "is the RAG
system actually working" is one curl away instead of a Python REPL session.
"""

from fastapi import APIRouter

from backend.services.personalized_rag_service import _get_rag, is_guideline_corpus_loaded
from backend.services.memory_service import _get_memory

router = APIRouter()


@router.get("/rag/status")
async def rag_status():
    """
    Reports both retrieval channels independently, since they fail
    independently: the guideline corpus is a local file/TF-IDF concern,
    mem0 is a database/embedding-model concern.
    """
    rag = _get_rag()
    guideline = {
        "loaded": is_guideline_corpus_loaded(),
        "stats": rag.stats() if rag else None,
    }

    mem = _get_memory()
    memory = {
        "available": mem is not None,
        "hint": None if mem is not None else (
            "mem0 failed to initialize — check startup logs for "
            "'[memory_service] mem0 init failed'. Common causes: missing "
            "sentence_transformers/psycopg2, or Postgres unreachable."
        ),
    }

    return {
        "guideline_corpus": guideline,
        "personal_memory": memory,
        "ready_for_personalized_answers": guideline["loaded"] and memory["available"],
    }
