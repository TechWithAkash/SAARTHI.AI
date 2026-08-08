"""
Cognitive Health Agent — DarpanAI Real-Time Agentic System.

4-step pipeline using Groq llama-3.3-70b-versatile.
Each step is a focused LLM call that builds on the previous.
Results stream in real-time via SSE so the frontend shows each
step as it actually completes — not fake delays on cached data.

Pipeline:
  Step 1 — Risk Analyst Agent       (Groq): Reads risk + SHAP → clinical summary
  Step 2 — Memory Agent             (mem0): Retrieves patterns + past interventions
  Step 3 — Causal Strategist Agent  (Groq): Root cause + intervention lever
  Step 4 — Recommendation Engine    (Groq): 3-5 ranked actions with mechanisms

Output stored in DB (agent_metadata JSONB) for the /recommend fallback.
"""

import json
import re
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, List, Optional

from groq import AsyncGroq

from backend.config import settings
from backend.db.postgres import get_db
from backend.services.memory_service import get_user_context

# ── Groq client ────────────────────────────────────────────────────────────────

_groq: Optional[AsyncGroq] = None

def _client() -> AsyncGroq:
    global _groq
    if _groq is None:
        _groq = AsyncGroq(api_key=settings.groq_api_key)
    return _groq


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _parse_json(raw: str, default):
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    m = re.search(r"[\[\{].*[\]\}]", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return default


def _pj(val, default):
    """Parse JSONB column (asyncpg returns strings)."""
    if val is None:
        return default
    return json.loads(val) if isinstance(val, str) else val


# ── Grounding estimated_risk_reduction in the real causal ATE (BP-3) ──────────
# The LLM used to be handed `"estimated_risk_reduction": 3.2` as a prompt
# example and duly invented a plausible number, which the frontend then rendered
# as an authoritative "-3.2 pts" badge. The number now comes from
# causal_service's Average Treatment Effect, or it is not shown at all.
#
# Attribution is by keyword because the LLM writes free-text actions; we match
# the action/reason/mechanism against each modifiable factor's vocabulary.
FACTOR_KEYWORDS = {
    "stress_level": ("stress", "cortisol", "anxiet", "meditat", "breath",
                     "mindful", "relax", "calm", "yoga"),
    "sleep":        ("sleep", "bed", "rest", "insomnia", "circadian", "nap",
                     "wind down", "screen time"),
    "steps":        ("step", "walk", "activity", "exercise", "cardio", "move",
                     "sedentary", "workout", "gym", "run", "cycl", "active"),
    "diet_score":   ("diet", "eat", "food", "sugar", "meal", "nutrition",
                     "carb", "glycemic", "glycaemic", "fibre", "fiber",
                     "processed", "vegetable", "protein"),
    "bmi":          ("weight", "bmi", "obes", "adipos", "waist", "calorie",
                     "caloric"),
}


def _attribute_factor(rec: Dict, factors: List[Dict]) -> Optional[Dict]:
    """
    Find which causal factor a recommendation is about.

    `factors` is causal_service's ranked_factors: [{factor, ate, chain,
    estimator}]. Returns the matched factor dict, or None when the text matches
    nothing — in which case the caller shows NO number rather than guessing.

    Matching is TIERED, and the tiers matter. `action` is what the patient
    actually changes, so it decides the factor on its own whenever it matches.
    Only if the action is uninformative do we fall back to reason/mechanism.

    Without that ordering, "Walk 8,000 steps daily — activity reduces BMI"
    gets attributed to bmi, because the mechanism names BMI as the downstream
    PATHWAY. But the intervention here is steps; BMI is what steps act through.
    Crediting the bmi ATE to a walking recommendation would report the wrong
    effect size.

    Within a single tier, a multi-factor match resolves to the largest |ate| —
    the lever the causal model says matters most among those genuinely mentioned.
    """
    by_name = {f.get("factor"): f for f in factors if f.get("factor")}
    if not by_name:
        return None

    def _match(text: str) -> List[Dict]:
        t = text.lower()
        if not t.strip():
            return []
        return [
            by_name[name] for name, words in FACTOR_KEYWORDS.items()
            if name in by_name and any(w in t for w in words)
        ]

    # Tier 1: the action itself. Tier 2: supporting rationale.
    for text in (
        str(rec.get("action", "")),
        " ".join(str(rec.get(k, "")) for k in ("reason", "causal_mechanism")),
    ):
        matched = _match(text)
        if matched:
            return max(matched, key=lambda f: abs(float(f.get("ate") or 0.0)))
    return None


def _ground_risk_reductions(recs: List[Dict], causal_row) -> List[Dict]:
    """
    Overwrites every recommendation's estimated_risk_reduction with a value
    derived from the causal model, or None.

    This runs AFTER parsing the LLM response and unconditionally discards
    whatever the model put there — the field is system-owned, not model-owned.
    `risk_reduction_source` records the provenance so the UI can style a real
    ATE differently from a weaker SHAP-derived prior.
    """
    factors = _pj(causal_row["ranked_factors"], []) if causal_row else []
    if not isinstance(factors, list):
        factors = []

    for rec in recs:
        match = _attribute_factor(rec, factors)
        if match is None:
            # Nothing to ground it in — refuse to show a number.
            rec["estimated_risk_reduction"] = None
            rec["risk_reduction_source"] = "unavailable"
            rec["causal_factor"] = None
            continue

        estimator = match.get("estimator", "unknown")
        ate = abs(float(match.get("ate") or 0.0))

        if estimator == "shap_prior":
            # Attribution-derived prior, not a causal effect. Still not an LLM
            # invention, but it must not be presented as an ATE.
            rec["estimated_risk_reduction"] = round(ate, 2)
            rec["risk_reduction_source"] = "shap_prior"
        elif estimator in ("dowhy_backdoor", "linear_backdoor"):
            rec["estimated_risk_reduction"] = round(ate, 2)
            rec["risk_reduction_source"] = "causal_ate"
        else:
            rec["estimated_risk_reduction"] = None
            rec["risk_reduction_source"] = "unavailable"

        rec["causal_factor"] = match.get("factor")
        rec["causal_estimator"] = estimator

    return recs


# ── Step 1: Risk Analyst ───────────────────────────────────────────────────────

async def _step_risk_analyst(risk_row, shap_row) -> Dict:
    if not risk_row:
        return {
            "risk_summary": "No health data available yet.",
            "critical_concerns": [],
            "severity_note": "",
            "error": True,
        }

    score = round(float(risk_row["risk_score"]), 1)
    category = risk_row["risk_category"]
    top_factors = _pj(risk_row["top_risk_factors"], [])
    shap = _pj(risk_row["shap_contributions"], {}) if risk_row else {}

    shap_lines = "\n".join(
        f"  {k}: {v:+.2f} pts ({'↑ risk' if v > 0 else '↓ protective'})"
        for k, v in sorted(shap.items(), key=lambda x: -abs(x[1]))
    )

    shap_desc = ""
    if shap_row:
        drivers = _pj(shap_row["risk_drivers"], [])
        protective = _pj(shap_row["protective_factors"], [])
        driver_names = [d.get("label", d.get("feature", "")) for d in drivers[:3]]
        prot_names   = [p.get("label", p.get("feature", "")) for p in protective[:2]]
        shap_desc = (
            f"Risk drivers: {', '.join(driver_names) or 'none identified'}\n"
            f"Protective factors: {', '.join(prot_names) or 'none'}"
        )

    prompt = f"""You are a clinical health risk analyst for DarpanAI's Cognitive Health Twin system.

PATIENT HEALTH SNAPSHOT:
  Risk Score: {score}/100  Category: {category}
  Top risk factors: {', '.join(top_factors)}

SHAP EXPLAINABILITY (each metric's contribution to risk score):
{shap_lines}

{shap_desc}

Provide a concise clinical analysis. Output ONLY valid JSON:
{{
  "risk_summary": "2-sentence clinical assessment of this patient's health state, referencing actual numbers",
  "critical_concerns": ["3 specific concerns with their values, e.g. stress_level at 7/10 is the primary driver"],
  "severity_note": "one sharp observation about the most alarming metric"
}}"""

    resp = await _client().chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": "You are a clinical health risk analyst. Output only valid JSON, no markdown."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=500,
        timeout=30,
    )
    raw = resp.choices[0].message.content
    result = _parse_json(raw, {
        "risk_summary": f"Risk score {score}/100 ({category}). Top factors: {', '.join(top_factors[:2])}.",
        "critical_concerns": top_factors[:3],
        "severity_note": f"Primary driver: {risk_row.get('primary_cause', 'unknown')}",
    })
    return result


# ── Step 2: Memory Agent ───────────────────────────────────────────────────────

async def _step_memory_agent(user_id: str) -> Dict:
    ctx = await get_user_context(
        user_id,
        query="health risk interventions sleep stress steps patterns what worked",
        limit=5,
    )
    memories = ctx.get("memories", [])
    if not memories:
        return {
            "summary": "No prior health history found. Recommendations based on current data only.",
            "key_insight": "First-time analysis — no personalisation from past interventions yet.",
            "memories": [],
            "count": 0,
        }
    texts = [m.get("text", "") for m in memories if m.get("text")]
    insight = texts[0][:120] + "…" if texts else "No patterns found."
    return {
        "summary": f"Retrieved {len(memories)} relevant memories from your health history.",
        "key_insight": insight,
        "memories": texts[:3],
        "count": len(memories),
    }


# ── Step 3: Causal Strategist ──────────────────────────────────────────────────

async def _step_causal_strategist(causal_row, step1: Dict, step2: Dict) -> Dict:
    if not causal_row:
        return {
            "primary_lever": "stress_level",
            "causal_mechanism": "cortisol spike → elevated resting HR → cardiovascular stress",
            "strategy": "Target stress reduction as primary intervention — insufficient causal history for personalised analysis.",
            "second_lever": "sleep",
        }

    ranked = _pj(causal_row["ranked_factors"], [])
    primary_cause = causal_row["primary_cause"] or "stress_level"
    causal_chain = causal_row["causal_chain"] or ""

    causal_lines = "\n".join(
        f"  {r['factor']}: ATE = {r.get('ate', 0):+.3f} pts per 1σ improvement | chain: {r.get('chain', '')}"
        for r in ranked[:5] if r.get("ate")
    ) or "  Insufficient observational history — using SHAP-based priors"

    memory_context = step2.get("key_insight", "No prior history.")

    prompt = f"""You are a causal health strategist using DoWhy causal inference methodology.

RISK ANALYSIS FROM STEP 1:
  Summary: {step1.get('risk_summary', '')}
  Critical concerns: {', '.join(step1.get('critical_concerns', []))}

CAUSAL INFERENCE RESULTS (DoWhy Average Treatment Effects):
  Primary causal chain: {primary_cause} → {causal_chain}
  Ranked intervention levers (most negative ATE = biggest benefit):
{causal_lines}

PERSONAL HISTORY INSIGHT:
  {memory_context}

Determine the optimal intervention strategy. Output ONLY valid JSON:
{{
  "primary_lever": "the single highest-impact modifiable factor name",
  "causal_mechanism": "biological pathway e.g. 'reduces cortisol → lowers resting HR → reduces CV risk'",
  "strategy": "1-sentence intervention strategy for this specific patient",
  "second_lever": "secondary factor to address"
}}"""

    resp = await _client().chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": "You are a causal health strategist. Output only valid JSON, no markdown."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=400,
        timeout=30,
    )
    result = _parse_json(resp.choices[0].message.content, {
        "primary_lever": primary_cause,
        "causal_mechanism": "multi-pathway physiological cascade",
        "strategy": f"Prioritise {primary_cause} via {causal_chain}",
        "second_lever": ranked[1]["factor"] if len(ranked) > 1 else "sleep",
    })
    return result


# ── Step 4: Recommendation Engine ─────────────────────────────────────────────

async def _step_recommendation_engine(
    step1: Dict,
    step2: Dict,
    step3: Dict,
    sim_row,
    risk_row,
    causal_row=None,
) -> Dict:
    # Build simulation summary
    sim_str = ""
    if sim_row:
        scenarios = _pj(sim_row["scenarios"], {})
        reductions = _pj(sim_row["projected_risk_reduction"], {})
        tl = _pj(sim_row["timeline_days"], [0, 15, 30, 45, 60, 90, 120])
        idx = {d: i for i, d in enumerate(tl)}
        # scenarios also carries a "by_disease" key (nested dict of per-disease
        # trajectories, added when simulation_service started reporting
        # diabetes/CVD/hypertension separately) — not a flat score list like
        # current/improved/optimal. Iterating scenarios.items() blindly and
        # indexing it as scores[2] raised KeyError: 2 on every real
        # simulation row. Only the three flat scalar trajectories belong here.
        for name in ("current", "improved", "optimal"):
            scores = scenarios.get(name)
            if scores:
                d30 = scores[idx.get(30, min(2, len(scores)-1))]
                d90 = scores[idx.get(90, min(5, len(scores)-1))]
                sim_str += f"  {name}: day-30={d30:.0f}, day-90={d90:.0f}, day-120={scores[-1]:.0f}\n"
        sim_str += f"  Projected reduction: improved={reductions.get('improved', 0):.1f}%, optimal={reductions.get('optimal', 0):.1f}%"

    memory_text = "\n".join(f"  - {m}" for m in step2.get("memories", [])[:3]) or "  No prior history."
    score = round(float(risk_row["risk_score"]), 1) if risk_row else 50

    prompt = f"""You are DarpanAI's personalized health advisor embedded in a Cognitive Health Twin system.

CLINICAL ANALYSIS:
  Risk score: {score}/100
  Summary: {step1.get('risk_summary', '')}
  Critical concerns: {'; '.join(step1.get('critical_concerns', []))}

CAUSAL STRATEGY:
  Primary intervention lever: {step3.get('primary_lever', '')}
  Biological mechanism: {step3.get('causal_mechanism', '')}
  Strategy: {step3.get('strategy', '')}
  Secondary lever: {step3.get('second_lever', '')}

SIMULATION PROJECTIONS:
{sim_str}

PERSONAL HEALTH HISTORY:
{memory_text}

RULES FOR RECOMMENDATIONS:
- SPECIFIC: "Walk 8,000 steps before 9 PM" not "exercise more"
- QUANTIFIED: cite actual numbers from the patient's data above
- RANKED: priority 1 = highest expected risk reduction
- MECHANISMS: explain the biological pathway for each action
- Generate exactly 4 recommendations
- Each action MUST clearly target one of these modifiable factors so it can be
  matched to the causal analysis: stress, sleep, steps/activity, diet, or weight.

CRITICAL: do NOT estimate any numeric risk reduction. Leave
"estimated_risk_reduction" as null. That field is computed by the system from
the causal model's measured Average Treatment Effect — a number you invent here
would be discarded, and if it were shown it would misrepresent the analysis.

Output ONLY a valid JSON array:
[
  {{
    "priority": 1,
    "action": "specific measurable action in 1 sentence",
    "reason": "why this for THIS patient, citing their actual numbers",
    "impact": "high",
    "timeframe": "2-3 weeks",
    "estimated_risk_reduction": null,
    "causal_mechanism": "reduces cortisol → lowers resting HR → reduces CV risk"
  }}
]"""

    resp = await _client().chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": "You are a personalized health advisor. Output only a valid JSON array, no markdown, no explanation."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=1200,
        timeout=45,
    )
    raw = resp.choices[0].message.content
    recs = _parse_json(raw, [])

    if not isinstance(recs, list):
        recs = []

    recs = [r for r in recs if isinstance(r, dict)]
    for i, r in enumerate(recs):
        r.setdefault("priority", i + 1)
        r.setdefault("impact", "medium")
        r.setdefault("timeframe", "2-4 weeks")
        r.setdefault("causal_mechanism", "")

    # System-owned: unconditionally replaces whatever the LLM produced.
    recs = _ground_risk_reductions(recs, causal_row)

    grounded = sum(1 for r in recs if r.get("estimated_risk_reduction") is not None)
    return {
        "recommendations": sorted(recs, key=lambda x: x.get("priority", 99)),
        "confidence": "high" if len(recs) >= 3 else "medium",
        "summary": (
            f"Generated {len(recs)} personalized interventions ranked by causal impact"
            + (f"; {grounded}/{len(recs)} with a measured effect size" if recs else "")
        ),
        "grounded_count": grounded,
    }


# ── DB persistence ─────────────────────────────────────────────────────────────

async def _store_result(
    pool,
    user_id: str,
    log_id: str,
    method: str,
    risk_score: Optional[float],
    recommendations: List,
    agent_metadata: Dict,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO recommendations
              (user_id, log_id, method, risk_score, recommendations, agent_metadata, generated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            user_id,
            log_id,
            method,
            float(risk_score) if risk_score is not None else None,
            json.dumps(recommendations),
            json.dumps(agent_metadata),
            datetime.now(timezone.utc),
        )


# ── Unified 4-step pipeline (ARC-3) ───────────────────────────────────────────
# stream_cognitive_agent() and run_cognitive_agent() previously duplicated ~90
# lines of the same 4 steps, and had already drifted: the streaming version had
# per-step try/except while the sync one had none, so a single Groq hiccup killed
# the entire background pipeline silently. The pipeline now exists ONCE here and
# both entry points consume it, which means they cannot drift again and both get
# the same error isolation.

STEP_META = [
    (1, "Risk Analyst",          "\U0001F52C", "Reading your health profile and SHAP explainability data\u2026"),
    (2, "Memory Agent",          "\U0001F9E0", "Searching your health history for patterns and past interventions\u2026"),
    (3, "Causal Strategist",     "\u26A1",     "Running causal inference to identify your primary risk lever\u2026"),
    (4, "Recommendation Engine", "\U0001F3AF", "Synthesising all evidence into personalised ranked interventions\u2026"),
]

TOOLS_CALLED = ["risk_analyst", "memory_agent", "causal_strategist", "recommendation_engine"]


async def _load_context(pool, user_id: str) -> Dict[str, Any]:
    """Every row the 4 steps need, in one connection acquisition."""
    async with pool.acquire() as conn:
        return {
            "log": await conn.fetchrow(
                "SELECT log_id FROM health_logs WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1", user_id),
            "risk": await conn.fetchrow(
                "SELECT * FROM risk_scores WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1", user_id),
            "shap": await conn.fetchrow(
                "SELECT * FROM explanations WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1", user_id),
            "causal": await conn.fetchrow(
                "SELECT * FROM causal_results WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 1", user_id),
            "sim": await conn.fetchrow(
                "SELECT * FROM simulations WHERE user_id=$1 ORDER BY generated_at DESC LIMIT 1", user_id),
        }


# Per-step fallbacks, used when a step raises. Keeping them here rather than
# inline means the streaming and sync paths degrade identically.
def _fallback(step: int, risk_score) -> Dict:
    return {
        1: {"risk_summary": f"Risk score {risk_score}/100. Analysis unavailable.",
            "critical_concerns": [], "severity_note": "", "error": True},
        2: {"summary": "Memory retrieval unavailable.", "key_insight": "",
            "memories": [], "count": 0},
        3: {"primary_lever": "stress_level",
            "causal_mechanism": "stress \u2192 elevated HR \u2192 CV risk",
            "strategy": "Target stress reduction as primary intervention.",
            "second_lever": "sleep"},
        4: {"recommendations": [], "confidence": "low",
            "summary": "Recommendation generation failed."},
    }[step]


async def _run_pipeline(user_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    The single source of truth for the agent pipeline.

    Yields progress events as dicts:
      {"kind": "error",         "message": str}
      {"kind": "step_start",    "step", "agent", "icon", "description"}
      {"kind": "step_complete", "step", "agent", "result"}
      {"kind": "done",          "recommendations", "agent_meta", "risk_score", "log_id"}

    The SSE endpoint formats these; the sync runner drains them for the final
    event. Neither reimplements a step.
    """
    pool = get_db()
    ctx = await _load_context(pool, user_id)

    if not ctx["log"]:
        yield {"kind": "error",
               "message": "No health data found. Submit a check-in from the Dashboard first."}
        return

    log_id = ctx["log"]["log_id"]
    risk_row, shap_row = ctx["risk"], ctx["shap"]
    causal_row, sim_row = ctx["causal"], ctx["sim"]
    risk_score = float(risk_row["risk_score"]) if risk_row else None

    trace: List[Dict] = []
    results: Dict[int, Dict] = {}

    for step, agent, icon, description in STEP_META:
        yield {"kind": "step_start", "step": step, "agent": agent,
               "icon": icon, "description": description}
        try:
            if step == 1:
                out = await _step_risk_analyst(risk_row, shap_row)
            elif step == 2:
                out = await _step_memory_agent(user_id)
            elif step == 3:
                out = await _step_causal_strategist(causal_row, results[1], results[2])
            else:
                out = await _step_recommendation_engine(
                    results[1], results[2], results[3], sim_row, risk_row, causal_row)
        except Exception as e:
            print(f"[cognitive_agent] Step {step} ({agent}) error: {type(e).__name__}: {e}")
            out = _fallback(step, risk_score)

        results[step] = out
        summary = out.get("risk_summary") or out.get("strategy") or out.get("summary") or ""
        detail = {"count": len(out.get("recommendations", []))} if step == 4 else out
        trace.append({"step": step, "agent": agent, "icon": icon,
                      "summary": summary, "detail": detail})
        yield {"kind": "step_complete", "step": step, "agent": agent, "result": out}

    step3, step4 = results[3], results[4]
    recs = step4.get("recommendations", [])

    agent_meta = {
        "reasoning": step3.get("strategy", ""),
        "primary_lever": step3.get("primary_lever", ""),
        "causal_mechanism": step3.get("causal_mechanism", ""),
        "agent_confidence": step4.get("confidence", "medium"),
        "tools_called": TOOLS_CALLED,
        # Derived, not hardcoded: this used to say 3 while listing 4 tools.
        "n_tool_calls": len(TOOLS_CALLED),
        # Provenance for the risk-reduction figures (BP-3)
        "causal_method": (causal_row["primary_cause"] and
                          _pj(causal_row["ranked_factors"], [{}])[0].get("estimator", "unknown")
                          if causal_row else "unavailable"),
        "grounded_recommendations": step4.get("grounded_count", 0),
        "trace": trace,
    }

    try:
        await _store_result(pool, user_id, log_id,
                            method=f"groq-agent:{settings.groq_model}",
                            risk_score=risk_score, recommendations=recs,
                            agent_metadata=agent_meta)
    except Exception as e:
        print(f"[cognitive_agent] DB store failed: {e}")

    yield {"kind": "done", "recommendations": recs, "agent_meta": agent_meta,
           "risk_score": risk_score, "log_id": log_id}


# ── SSE stream (primary \u2014 real-time) ─────────────────────────────────────

async def stream_cognitive_agent(user_id: str) -> AsyncGenerator[str, None]:
    """
    Formats the shared pipeline as SSE. Event shapes are unchanged from the
    original implementation \u2014 AgentTrace.tsx depends on these exact keys.
    """
    async for ev in _run_pipeline(user_id):
        kind = ev["kind"]

        if kind == "error":
            yield _sse({"type": "error", "message": ev["message"]})

        elif kind == "step_start":
            yield _sse({"type": "step_start", "step": ev["step"], "agent": ev["agent"],
                        "icon": ev["icon"], "description": ev["description"]})

        elif kind == "step_complete":
            r, step = ev["result"], ev["step"]
            payload = {"type": "step_complete", "step": step, "agent": ev["agent"]}
            if step == 1:
                payload["summary"] = r.get("risk_summary", "")
                payload["severity"] = r.get("severity_note", "")
            elif step == 2:
                payload["summary"] = r.get("summary", "")
                payload["insight"] = r.get("key_insight", "")
            elif step == 3:
                payload["summary"] = r.get("strategy", "")
                payload["lever"] = r.get("primary_lever", "")
                payload["mechanism"] = r.get("causal_mechanism", "")
            else:
                payload["summary"] = r.get("summary", "")
            yield _sse(payload)

        elif kind == "done":
            yield _sse({"type": "complete",
                        "recommendations": ev["recommendations"],
                        "agent": ev["agent_meta"],
                        "risk_score": ev["risk_score"],
                        "method": f"groq-agent:{settings.groq_model}"})


# ── Synchronous run (for the background pipeline) ─────────────────────────────

async def run_cognitive_agent(user_id: str, log_id: str) -> Dict[str, Any]:
    """
    Non-streaming entry point. Drains the same pipeline the SSE endpoint uses,
    so the two cannot produce different results.
    """
    final = None
    async for ev in _run_pipeline(user_id):
        if ev["kind"] == "error":
            return {"user_id": user_id, "log_id": log_id,
                    "generated_at": datetime.now(timezone.utc),
                    "error": ev["message"], "recommendations": [], "agent": None}
        if ev["kind"] == "done":
            final = ev

    if final is None:
        return {"user_id": user_id, "log_id": log_id,
                "generated_at": datetime.now(timezone.utc),
                "error": "pipeline produced no result",
                "recommendations": [], "agent": None}

    return {
        "user_id": user_id,
        "log_id": final["log_id"],
        "generated_at": datetime.now(timezone.utc),
        "method": f"groq-agent:{settings.groq_model}",
        "risk_score": final["risk_score"],
        "recommendations": final["recommendations"],
        "agent": final["agent_meta"],
    }
