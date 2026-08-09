"""
Chat Service — DarpanAI Agentic Health Chat.

Streams word-by-word responses via Groq with full patient health context
injected from the DB. Generates contextual follow-up chips after each reply.
Persists conversations in mem0 for cross-session memory.
"""

import json
import asyncio
from typing import AsyncGenerator, List, Dict, Optional

from groq import AsyncGroq, RateLimitError, APIConnectionError, APITimeoutError

from backend.config import settings
from backend.db.postgres import get_db
from backend.services.memory_service import get_user_context
from backend.services.doc_rag_service import retrieve_context
from backend.services.personalized_rag_service import format_guideline_context

_groq: Optional[AsyncGroq] = None


def _client() -> AsyncGroq:
    global _groq
    if _groq is None:
        _groq = AsyncGroq(api_key=settings.groq_api_key)
    return _groq


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _pj(val, default):
    if val is None:
        return default
    return json.loads(val) if isinstance(val, str) else val


async def _fetch_health_context(user_id: str) -> Dict:
    pool = get_db()
    async with pool.acquire() as conn:
        risk_row = await conn.fetchrow(
            "SELECT * FROM risk_scores WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1", user_id
        )
        shap_row = await conn.fetchrow(
            "SELECT * FROM explanations WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1", user_id
        )
        causal_row = await conn.fetchrow(
            "SELECT * FROM causal_results WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1", user_id
        )
        sim_row = await conn.fetchrow(
            "SELECT * FROM simulations WHERE user_id=$1 ORDER BY generated_at DESC LIMIT 1", user_id
        )
        health_row = await conn.fetchrow(
            "SELECT * FROM health_logs WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1", user_id
        )

    return {
        "risk": risk_row,
        "shap": shap_row,
        "causal": causal_row,
        "sim": sim_row,
        "health": health_row,
    }


def _build_system_prompt(
    ctx: Dict,
    memories: List[str],
    doc_context: Optional[str] = None,
    guideline_context: Optional[str] = None,
) -> str:
    risk = ctx.get("risk")
    shap = ctx.get("shap")
    causal = ctx.get("causal")
    sim = ctx.get("sim")
    health = ctx.get("health")

    # Risk section
    if risk:
        score = round(float(risk["risk_score"]), 1)
        category = risk["risk_category"]
        top_factors = _pj(risk["top_risk_factors"], [])
        risk_section = f"Risk Score: {score}/100 ({category})\nTop risk factors: {', '.join(top_factors)}"
    else:
        # Deliberately explicit rather than just "Not yet assessed" — found by
        # testing this end-to-end for a user with genuinely zero data anywhere
        # (SQL and mem0 both empty): the model still confidently claimed a
        # specific "primary cause of your risk score" with nothing behind it.
        # A vague absence in the prompt wasn't enough to stop it from filling
        # the gap with something plausible-sounding.
        risk_section = (
            "Risk Score: NO DATA — this patient has not submitted a health "
            "check-in yet. Do not state or imply a risk score, category, or "
            "primary risk factor. Tell them plainly that no assessment "
            "exists yet and invite them to submit vitals."
        )

    # SHAP section
    shap_section = ""
    if shap:
        raw_contributions = _pj(shap["shap_contributions"], {})
        # explain_service.py's Block A rewrite started storing a nested
        # structure here — {icmr, legacy, per_disease, explains,
        # explained_fraction} — but this code still expected the old flat
        # {feature: value} shape directly. Reading the dict-valued "icmr" or
        # "per_disease" entries as if they were numbers crashed every chat
        # request with TypeError: bad operand type for abs(): 'dict',
        # surfacing to users as a generic "Connection failed" — nothing to
        # do with the Groq API key. "legacy" is the flat view chat_service
        # needs; the isinstance filter is a defensive fallback for either
        # shape so a future field-shape change degrades instead of crashing.
        contributions = raw_contributions.get("legacy", raw_contributions)
        contributions = {
            k: v for k, v in contributions.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        }
        drivers = _pj(shap["risk_drivers"], [])
        protective = _pj(shap["protective_factors"], [])
        shap_lines = "\n".join(
            f"  • {k}: {v:+.2f} pts ({'increases' if v > 0 else 'reduces'} risk)"
            for k, v in sorted(contributions.items(), key=lambda x: -abs(x[1]))[:6]
        ) or "  (no per-feature breakdown available)"
        driver_names = [d.get("label", d.get("feature", "")) for d in drivers[:3]]
        prot_names = [p.get("label", p.get("feature", "")) for p in protective[:2]]
        shap_section = f"""
SHAP Explainability (each factor's contribution):
{shap_lines}
Primary risk drivers: {', '.join(driver_names)}
Protective factors: {', '.join(prot_names)}"""

    # Causal section
    causal_section = ""
    if causal:
        primary = causal["primary_cause"] or "unknown"
        chain = causal["causal_chain"] or "not determined"
        ranked = _pj(causal["ranked_factors"], [])
        top_lever = ranked[0] if ranked else {}
        causal_section = f"""
Causal Analysis (DoWhy):
  Primary cause: {primary}
  Causal chain: {chain}
  Top intervention lever: {top_lever.get('factor', primary)} (ATE: {top_lever.get('ate', 0):+.3f} pts/σ)"""

    # Simulation section
    sim_section = ""
    if sim:
        reductions = _pj(sim["projected_risk_reduction"], {})
        improved = reductions.get("improved", 0)
        optimal = reductions.get("optimal", 0)
        sim_section = f"""
120-Day Simulation Projections:
  Target Improvement scenario: -{improved:.1f}% risk reduction
  Optimal Equilibrium scenario: -{optimal:.1f}% risk reduction"""

    # Health vitals
    vitals_section = ""
    if health:
        vitals_section = f"""
Current Vitals:
  Heart rate: {health.get('heart_rate', '?')} bpm | Sleep: {health.get('sleep', '?')}h
  Steps: {int(health.get('steps', 0)):,}/day | Stress: {health.get('stress_level', '?')}/10
  Diet score: {health.get('diet_score', '?')}/10 | BMI: {health.get('bmi', '?')}"""

    # Memory section
    memory_section = ""
    if memories:
        memory_lines = "\n".join(f"  {i+1}. {m}" for i, m in enumerate(memories[:5]))
        memory_section = f"""
Health History (from mem0):
{memory_lines}"""
    else:
        memory_section = "\nHealth History: First session — no prior history yet."

    # Document context block (injected at top when present)
    doc_section = ""
    if doc_context:
        doc_section = f"""
{doc_context}

"""

    doc_instructions = ""
    if doc_context:
        doc_instructions = """
• A medical document has been uploaded — PRIORITIZE information from it
• Quote specific lab values, dates, and findings verbatim from the document
• Cross-reference document findings against the patient's live risk profile"""

    # Clinical-guideline RAG (rag.py, via personalized_rag_service). Kept as
    # its own block, never merged into PATIENT HEALTH PROFILE above — the
    # distinction between "what the guideline says generally" and "what
    # this patient's own data shows" is exactly the thing a health app must
    # never blur, and the instructions below say so explicitly.
    guideline_section = f"\n{guideline_context}\n" if guideline_context else ""
    guideline_instructions = ""
    if guideline_context:
        guideline_instructions = """
• When citing the CLINICAL GUIDELINE CONTEXT, mark it as general evidence (e.g. "guidelines suggest...")
• Never present a guideline citation as if it were this patient's own measured data
• Cite excerpts as [G1], [G2] etc. matching the labels shown"""

    return f"""You are Darpan, the Agentic Cognitive Health Twin assistant built into DarpanAI.
You have full access to this patient's health data and speak with clinical precision combined with empathy.
{doc_section}{guideline_section}
═══ PATIENT HEALTH PROFILE ═══
{risk_section}
{vitals_section}
{shap_section}
{causal_section}
{sim_section}
{memory_section}

═══ YOUR CAPABILITIES ═══
• Explain any metric in depth (SHAP contributions, causal pathways, risk factors)
• Answer what-if questions ("what if my stress drops to 3?") using the patient's data
• Interpret simulation projections and recommend specific interventions
• Explain the causal chain driving their risk
• Compare current readings to healthy benchmarks{doc_instructions}{guideline_instructions}

═══ RULES ═══
• Always reference the patient's ACTUAL numbers, not generic advice
• If Risk Score says NO DATA, never invent a score, category, or "primary cause" — say plainly that none exists yet
• Use markdown for structure when helpful (bold, bullet points)
• Keep responses focused and under 200 words unless depth is needed
• Never prescribe medications — lifestyle and behavioral interventions only
• If asked about something outside health, gently redirect to health topics
• Be direct and confident — this patient trusts your analysis"""


async def _generate_chips(message: str, reply: str, health_summary: str) -> List[str]:
    """Generate 3 contextual follow-up question chips based on the conversation."""
    try:
        prompt = f"""Based on this health assistant conversation, generate exactly 3 short follow-up questions the user would naturally want to ask next.

User asked: "{message}"
Assistant replied: "{reply[:300]}..."
Patient context: {health_summary}

Rules:
- Each question must be under 10 words
- Make them specific to the patient's actual data
- Mix: one deep-dive, one action-oriented, one comparative
- Output ONLY a JSON array of 3 strings, nothing else

Example format: ["Why is stress my main driver?", "What if I sleep 8 hours?", "How does this compare to last week?"]"""

        resp = await _client().chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150,
            timeout=15,
        )
        raw = resp.choices[0].message.content.strip()
        import re
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            chips = json.loads(m.group())
            return chips[:3] if isinstance(chips, list) else []
    except Exception as e:
        print(f"[chat_service] chips generation failed: {e}")

    return [
        "What's driving my risk score?",
        "Which metric should I fix first?",
        "What does my causal chain mean?",
    ]


async def _store_conversation_in_mem0(user_id: str, user_msg: str, assistant_reply: str) -> None:
    """
    Intentionally skipped: mem0's internal extraction prompt exceeds Groq's 6k TPM
    free-tier limit regardless of input size. Health context is already persisted in
    PostgreSQL and injected directly into every system prompt — mem0 conv storage
    is redundant and causes repeated 413 errors.
    """
    pass





async def stream_chat(
    user_id: str,
    message: str,
    history: List[Dict],
    doc_session_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Stream a chat response word-by-word via SSE.

    SSE event types:
      {"type": "token", "content": "word "}   — streamed response tokens
      {"type": "done", "chips": [...]}         — final event with follow-up chips
      {"type": "error", "message": "..."}      — on failure

    When doc_session_id is provided, the top-4 most relevant document chunks
    are retrieved and injected into the system prompt as primary evidence.
    """
    # Fetch health context
    try:
        ctx = await asyncio.wait_for(_fetch_health_context(user_id), timeout=8.0)
    except Exception as e:
        yield _sse({"type": "error", "message": f"Failed to load health context: {e}"})
        return

    # Fetch mem0 memories independently — optional
    mem_ctx: dict = {}
    try:
        mem_ctx = await asyncio.wait_for(
            get_user_context(user_id, query=message, limit=6),
            timeout=5.0,
        )
    except Exception as e:
        print(f"[chat_service] mem0 skipped (non-fatal): {e}")

    memories = [m.get("text", "") for m in mem_ctx.get("memories", []) if m.get("text")]

    # Retrieve document context if a session is loaded
    doc_context: Optional[str] = None
    if doc_session_id:
        doc_context = retrieve_context(doc_session_id, message, top_k=4)

    # Static clinical-guideline retrieval (rag.py, via personalized_rag_service).
    # Independent of mem0 — this is TF-IDF over documents, not a network call —
    # so a slow/failing guideline lookup should never block the chat response.
    guideline_context: Optional[str] = None
    try:
        guideline_context = format_guideline_context(message, top_k=4)
    except Exception as e:
        print(f"[chat_service] guideline RAG skipped (non-fatal): {e}")

    system_prompt = _build_system_prompt(ctx, memories, doc_context=doc_context, guideline_context=guideline_context)

    # Build message list (last 8 turns to stay within token budget)
    msgs = [{"role": "system", "content": system_prompt}]
    for h in history[-8:]:
        msgs.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    msgs.append({"role": "user", "content": message})

    full_reply = ""

    try:
        stream = await _client().chat.completions.create(
            model=settings.groq_model,
            messages=msgs,
            temperature=0.35,
            max_tokens=600,
            stream=True,
            timeout=45,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                full_reply += delta
                yield _sse({"type": "token", "content": delta})

    except RateLimitError as e:
        # A real, external constraint (Groq's free-tier daily token quota),
        # not a bug — the generic "temporarily unavailable" message this used
        # to fall through to made it look broken instead of just rate-capped
        # for the day. Named here so it's honest about what's actually true.
        print(f"[chat_service] Groq rate limit: {e}")
        yield _sse({"type": "error", "message": "Darpan has hit its daily AI usage limit. This resets on its own — please try again in a little while."})
        return
    except (APIConnectionError, APITimeoutError) as e:
        print(f"[chat_service] Groq connection error: {e}")
        yield _sse({"type": "error", "message": "Couldn't reach the AI service — check your connection and try again."})
        return
    except Exception as e:
        print(f"[chat_service] stream error: {e}")
        yield _sse({"type": "error", "message": "Darpan is temporarily unavailable. Please try again."})
        return

    # Generate follow-up chips and store in mem0 concurrently
    risk = ctx.get("risk")
    health_summary = f"risk={round(float(risk['risk_score']), 1)}/100" if risk else "no data"

    chips, _ = await asyncio.gather(
        _generate_chips(message, full_reply, health_summary),
        _store_conversation_in_mem0(user_id, message, full_reply),
    )

    yield _sse({"type": "done", "chips": chips})
