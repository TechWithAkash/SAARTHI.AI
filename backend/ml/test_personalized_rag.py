"""
Personalized RAG integration tests — Garmin-sourced check-in -> mem0 memory ->
chat system prompt, plus the clinical-guideline retrieval layer (rag.py,
reused unmodified).

Uses a throwaway test user, cleaned up before and after — never touches
user_demo_001 or any real account data.

Run: PYTHONPATH=. /opt/anaconda3/envs/darpanai/bin/python3 backend/ml/test_personalized_rag.py
"""

import os
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(v, "1")

import asyncio
import inspect

passed = failed = 0
TEST_USER = "__test_personalized_rag_user__"


def ok(label, cond):
    global passed, failed
    passed, failed = passed + bool(cond), failed + (not cond)
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")


async def cleanup(conn, user_id: str):
    for table, col in (
        ("anomalies", "log_id"), ("explanations", "log_id"),
        ("simulations", "based_on_log_id"), ("risk_scores", "log_id"),
        ("recommendations", "log_id"), ("health_logs", "log_id"),
    ):
        await conn.execute(
            f"DELETE FROM {table} WHERE {col} IN "
            f"(SELECT log_id FROM health_logs WHERE user_id=$1)", user_id,
        ) if table != "health_logs" else None
    await conn.execute("DELETE FROM health_logs WHERE user_id=$1", user_id)
    await conn.execute("DELETE FROM users WHERE user_id=$1", user_id)
    from backend.services.memory_service import delete_user_memories
    await delete_user_memories(user_id)


async def main():
    import asyncpg
    from backend.config import settings
    from backend.db.postgres import connect_db, close_db, get_db
    from backend.models.health import HealthDataInput
    from backend.services.ingestion_service import ingest
    from backend.routes.health_data import run_full_pipeline, _PIPELINE_STATUS
    from backend.services.memory_service import get_user_context
    from backend.services.personalized_rag_service import (
        get_personalized_context, is_guideline_corpus_loaded,
        format_guideline_context, get_guideline_chunks,
    )
    from backend.services.chat_service import _build_system_prompt

    await connect_db()
    conn = await asyncpg.connect(settings.database_url)

    try:
        await cleanup(conn, TEST_USER)
        await conn.execute(
            "INSERT INTO users (user_id, age, gender) VALUES ($1, 30, 'male')", TEST_USER,
        )

        print("\n1. rag.py reuse — imports and degrades gracefully")
        from rag import ClinicalRAG
        ok("ClinicalRAG importable from repo root (rag.py, unmodified)", ClinicalRAG is not None)
        ok("personalized_rag_service does not redefine chunking/retrieval logic "
           "(reuses rag.py's classes, doesn't reimplement them)",
           "TfidfVectorizer" not in inspect.getsource(
               __import__("backend.services.personalized_rag_service", fromlist=["x"])))
        # Corpus presence is environment-dependent (guideline_corpus/ is built
        # from research_papers/*.pdf via build_guideline_corpus.py, and may or
        # may not have been run yet) — assert honesty in BOTH states rather
        # than hardcoding one, same pattern as the OpenAQ key check elsewhere.
        corpus_present = is_guideline_corpus_loaded()
        print(f"  (guideline corpus {'is' if corpus_present else 'is not'} loaded in this environment)")

        chunks = get_guideline_chunks("does hypertension relate to serum ferritin levels")
        if corpus_present:
            ok("corpus loaded -> real chunks retrieved for an on-topic query", len(chunks) > 0)
            ok("retrieved chunks carry real source/score metadata",
               all("source" in c and "score" in c for c in chunks))
        else:
            ok("no corpus -> empty chunks, no crash", chunks == [])

        ctx_block = format_guideline_context("does hypertension relate to serum ferritin levels")
        if corpus_present:
            ok("corpus loaded -> context block is real extracted text, not None",
               ctx_block is not None and "CLINICAL GUIDELINE CONTEXT" in ctx_block)
        else:
            ok("no corpus -> None context block (not fabricated content)", ctx_block is None)

        # TF-IDF is lexical, not semantic (same known limitation as
        # doc_rag_service.py) — a genuinely off-topic query sharing a common
        # word ("best") WILL still retrieve something, scored on that shared
        # word alone. That's inherent to the retrieval method rag.py uses,
        # not a bug to chase here. What should actually hold is the relative
        # ordering: an on-topic query scores its top match higher than an
        # off-topic query scores its best (accidental) match.
        on_topic_top = get_guideline_chunks("serum ferritin and hypertension risk", top_k=1)
        off_topic_top = get_guideline_chunks("what is the best pizza topping", top_k=1)
        if on_topic_top and off_topic_top:
            ok("on-topic relevance clearly exceeds an off-topic lexical accident",
               on_topic_top[0]["score"] > off_topic_top[0]["score"])
        else:
            ok("on-topic query retrieves at least one chunk", bool(on_topic_top))

        print("\n2. mem0/pgvector — the 'appropriate vector storage layer'")
        from backend.services.memory_service import _get_memory
        mem = _get_memory()
        ok("mem0 actually initializes (was previously broken: missing "
           "sentence_transformers + psycopg2)", mem is not None)

        print("\n3. Real Garmin-sourced check-in flows end-to-end into mem0")
        payload = HealthDataInput(
            user_id=TEST_USER, source="garmin",
            heart_rate=68, steps=9500, sleep=7.2, bmi=22.8,
            stress_level=3, diet_score=7,
            hrv_rmssd=55.0,
        )
        result = await ingest(payload)
        ok("ingestion succeeds", "log_id" in result)

        await run_full_pipeline(
            result["log_id"], TEST_USER, result["raw"], result["normalized"], anomalies=[],
        )

        stage_status = _PIPELINE_STATUS.get(result["log_id"], {}).get("stages", {})
        ok("pipeline recorded a 'memory' stage", "memory" in stage_status)
        ok("memory stage succeeded", stage_status.get("memory", {}).get("ok") is True)

        mem_ctx = await get_user_context(TEST_USER, query="how has my activity been")
        ok("mem0 now has real memories for this Garmin-sourced check-in", mem_ctx["count"] > 0)
        ok("retrieved memory reflects the real submitted data (not fabricated)",
           any("9,500" in m["text"] or "9500" in m["text"] or "active" in m["text"].lower()
               for m in mem_ctx["memories"]))

        print("\n4. Combined personalized context (mem0 + guideline retrieval)")
        combined = await get_personalized_context(TEST_USER, "how is my heart rate trending")
        ok("returns both channels", set(combined.keys()) >= {
            "guideline_context", "guideline_corpus_loaded",
            "personal_memories", "personal_memory_source"})
        ok("personal_memories populated from the real check-in", len(combined["personal_memories"]) > 0)
        ok("personal_memory_source is mem0, not the empty fallback",
           combined["personal_memory_source"] == "mem0")

        print("\n5. chat_service system prompt keeps guideline and patient context separate")
        prompt = _build_system_prompt(
            ctx={}, memories=combined["personal_memories"],
            guideline_context="═══ CLINICAL GUIDELINE CONTEXT (general population evidence, not this patient's data) ═══\n[G1] Test Source | GENERAL\n    Sample guideline text.",
        )
        ok("guideline block present and labelled as general evidence",
           "CLINICAL GUIDELINE CONTEXT" in prompt and "not this patient's data" in prompt)
        ok("instructs the model never to present a citation as the patient's own data",
           "Never present a guideline citation as if it were this patient's own measured data" in prompt)
        ok("patient profile section still present and distinct from guideline section",
           "PATIENT HEALTH PROFILE" in prompt)

        no_guideline_prompt = _build_system_prompt(ctx={}, memories=[], guideline_context=None)
        ok("no guideline context -> no guideline section injected (honest, not padded)",
           "CLINICAL GUIDELINE CONTEXT" not in no_guideline_prompt)

    finally:
        await cleanup(conn, TEST_USER)
        await conn.close()
        await close_db()

    print(f"\n{'='*58}\n  {passed} passed, {failed} failed\n{'='*58}")


if __name__ == "__main__":
    asyncio.run(main())
    raise SystemExit(1 if failed else 0)
