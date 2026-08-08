"""
Recommendation Engine — DarpanAI Phase 10.

Uses Groq (llama-3.3-70b-versatile) to generate personalised, ranked,
actionable health recommendations by synthesising:

  - Current risk score + category
  - SHAP feature contributions (what's driving risk TODAY)
  - DoWhy causal effects (what to FIX for the biggest impact)
  - Simulation projections (what happens in 30/60/90 days if they act)
  - mem0 memory context (what has worked for this user before)

Output: 3–5 ranked recommendations, each with:
  - priority (1 = most impactful)
  - action (specific, measurable, 1 sentence)
  - reason (why THIS for THIS user — references their data)
  - impact (high / medium / low)
  - timeframe (realistic estimate)
  - estimated_risk_reduction (float, from causal ATE)
"""

import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from groq import AsyncGroq

from backend.config import settings
from backend.db.postgres import get_db
from backend.services.memory_service import get_user_context, format_context_for_llm

_groq_client: Optional[AsyncGroq] = None


def _get_client() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=settings.groq_api_key)
    return _groq_client


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    return """You are SAARTHI.AI's health recommendation engine — a precision health advisor.

Your job: given a user's health data, generate 3–5 ranked, personalised, actionable recommendations.

Rules:
- Be SPECIFIC: say "Sleep 7.5–8 hours by 10:30pm" not "sleep more"
- Be QUANTIFIED: reference actual numbers from the user's data
- Rank by expected risk reduction (biggest impact first)
- Explain WHY using causal logic, not generic advice
- Keep each action to 1 concise sentence
- Each reason must reference the user's specific data
- Timeframe must be realistic (habits take weeks, not days)
- Never invent data — only use what is provided

Output ONLY a valid JSON array. No markdown, no explanation, no preamble.

Schema:
[
  {
    "priority": 1,
    "action": "string — specific measurable action",
    "reason": "string — references user's actual numbers",
    "impact": "high|medium|low",
    "timeframe": "string — e.g. '2–3 weeks'",
    "estimated_risk_reduction": float
  }
]"""


def _build_user_prompt(
    user_profile:       Dict,
    risk_result:        Dict,
    shap_result:        Dict,
    causal_result:      Dict,
    simulation_result:  Dict,
    memory_context:     str,
) -> str:
    risk_score    = risk_result.get("risk_score", 50)
    risk_category = risk_result.get("risk_category", "Moderate")
    top_factors   = risk_result.get("top_risk_factors", [])

    shap = shap_result.get("shap_contributions", {})
    shap_sorted = sorted(shap.items(), key=lambda x: -abs(x[1]))
    shap_str = ", ".join(f"{k}: {v:+.1f} pts" for k, v in shap_sorted[:5])

    causal_ranked = causal_result.get("ranked_factors", [])
    causal_str = "\n".join(
        f"  - Improving {r['factor']} by 1σ → estimated {r['ate']:+.1f} risk pts | chain: {r['chain']}"
        for r in causal_ranked[:5]
        if r.get("ate")
    ) or "  Insufficient history — using SHAP priors"

    scenarios   = simulation_result.get("scenarios", {})
    timeline    = simulation_result.get("timeline_days", [0, 30, 60, 90, 120])
    proj_reduce = simulation_result.get("projected_risk_reduction", {})

    sim_str = ""
    if scenarios:
        day_idx = {d: i for i, d in enumerate(timeline)}
        d30 = day_idx.get(30, 1)
        d90 = day_idx.get(90, 3)
        sim_str = (
            f"  Current path (no change): "
            f"Day 30={scenarios.get('current', [risk_score]*5)[d30]:.0f}, "
            f"Day 90={scenarios.get('current', [risk_score]*5)[d90]:.0f}\n"
            f"  Improved path (sleep+steps): "
            f"Day 30={scenarios.get('improved', [risk_score]*5)[d30]:.0f}, "
            f"Day 90={scenarios.get('improved', [risk_score]*5)[d90]:.0f} "
            f"({proj_reduce.get('improved', 0):+.1f}% total)\n"
            f"  Optimal path (all factors): "
            f"Day 30={scenarios.get('optimal', [risk_score]*5)[d30]:.0f}, "
            f"Day 90={scenarios.get('optimal', [risk_score]*5)[d90]:.0f} "
            f"({proj_reduce.get('optimal', 0):+.1f}% total)"
        )

    age    = user_profile.get("age", 35)
    gender = user_profile.get("gender", "unknown")
    goals  = ", ".join(user_profile.get("health_goals", ["general wellness"]))

    return f"""USER PROFILE:
  Age: {age} | Gender: {gender}
  Health goals: {goals}

CURRENT HEALTH STATUS:
  Risk score: {risk_score:.0f}/100 ({risk_category})
  Top risk factors: {', '.join(top_factors)}

SHAP CONTRIBUTIONS (what's driving risk right now):
  {shap_str}

CAUSAL ANALYSIS (estimated risk reduction per 1σ improvement):
{causal_str}

SIMULATION PROJECTIONS:
{sim_str}

PERSONAL HEALTH MEMORY:
{memory_context}

Generate 3–5 ranked recommendations. Output only the JSON array."""


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_recommendations(raw: str) -> List[Dict]:
    """Extract JSON array from Groq response, handling common formatting issues."""
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()

    # Find the JSON array
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON array found in response: {raw[:200]}")

    data = json.loads(match.group())

    # Validate and normalise each recommendation
    validated = []
    for i, rec in enumerate(data):
        validated.append({
            "priority":                 int(rec.get("priority", i + 1)),
            "action":                   str(rec.get("action", "")),
            "reason":                   str(rec.get("reason", "")),
            "impact":                   str(rec.get("impact", "medium")).lower(),
            "timeframe":                str(rec.get("timeframe", "2–4 weeks")),
            "estimated_risk_reduction": float(rec.get("estimated_risk_reduction", 0.0)),
        })

    return sorted(validated, key=lambda x: x["priority"])


def _fallback_recommendations(
    risk_result: Dict,
    causal_result: Dict,
) -> List[Dict]:
    """Rule-based fallback when Groq is unavailable."""
    ranked = causal_result.get("ranked_factors", [])
    recs   = []

    ACTIONS = {
        "stress_level": {
            "action":   "Practice 10 minutes of box breathing or meditation daily",
            "reason":   "Stress is your #1 modifiable risk driver via the stress → heart rate pathway",
            "impact":   "high",
            "timeframe": "1–2 weeks",
        },
        "sleep": {
            "action":   "Set a fixed sleep schedule: in bed by 10:30pm, wake at 6:30am",
            "reason":   "Sleep deficit elevates resting heart rate and disrupts diet quality",
            "impact":   "high",
            "timeframe": "2–3 weeks",
        },
        "steps": {
            "action":   "Add a 30-minute walk after dinner — target 8,000 steps daily",
            "reason":   "Steps directly reduce BMI and improve sleep quality",
            "impact":   "medium",
            "timeframe": "3–4 weeks",
        },
        "diet_score": {
            "action":   "Replace one processed meal per day with whole foods",
            "reason":   "Diet quality affects BMI and downstream cardiovascular risk",
            "impact":   "medium",
            "timeframe": "2–4 weeks",
        },
        "bmi": {
            "action":   "Combine caloric awareness with daily movement — aim for -0.5 BMI/month",
            "reason":   "BMI reduction lowers resting heart rate and long-term CV risk",
            "impact":   "high",
            "timeframe": "4–8 weeks",
        },
    }

    for i, factor in enumerate(ranked[:4], 1):
        f   = factor.get("factor", "")
        ate = factor.get("ate", 0.0)
        tmpl = ACTIONS.get(f)
        if tmpl:
            recs.append({
                "priority":                 i,
                "action":                   tmpl["action"],
                "reason":                   tmpl["reason"],
                "impact":                   tmpl["impact"],
                "timeframe":                tmpl["timeframe"],
                "estimated_risk_reduction": abs(ate),
            })

    if not recs:
        recs.append({
            "priority": 1,
            "action":   "Track sleep, steps, and stress daily for 7 days",
            "reason":   "Consistent tracking is the first step to understanding your patterns",
            "impact":   "medium",
            "timeframe": "1 week",
            "estimated_risk_reduction": 0.0,
        })

    return recs


# ── helpers to deserialise JSONB columns ──────────────────────────────────────

def _json_field(row, field: str, default):
    """Safe JSONB deserialisation — asyncpg returns JSONB columns as strings."""
    if row is None:
        return default
    raw = row[field]
    if raw is None:
        return default
    if isinstance(raw, str):
        return json.loads(raw)
    return raw  # already parsed (future asyncpg versions may return native types)


# ── Main service ──────────────────────────────────────────────────────────────

async def generate_recommendations(
    user_id: str,
    log_id:  str,
) -> Dict[str, Any]:
    pool = get_db()

    async with pool.acquire() as conn:
        # risk_scores — most recent for this user (log_id match preferred)
        risk_row = await conn.fetchrow(
            """
            SELECT risk_score, risk_category, top_risk_factors, shap_contributions,
                   primary_cause, causal_chain
            FROM risk_scores
            WHERE user_id = $1
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            user_id,
        )

        # simulations — most recent
        simulation_row = await conn.fetchrow(
            """
            SELECT scenarios, timeline_days, projected_risk_reduction
            FROM simulations
            WHERE user_id = $1
            ORDER BY generated_at DESC
            LIMIT 1
            """,
            user_id,
        )

        # causal_results — most recent
        causal_row = await conn.fetchrow(
            """
            SELECT ranked_factors, primary_cause, causal_chain
            FROM causal_results
            WHERE user_id = $1
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            user_id,
        )

        # users
        user_row = await conn.fetchrow(
            "SELECT * FROM users WHERE user_id = $1",
            user_id,
        )

    # ── Assemble dicts (deserialise JSONB strings) ────────────────────────────

    risk_result: Dict = {
        "risk_score":        risk_row["risk_score"]        if risk_row else 50,
        "risk_category":     risk_row["risk_category"]     if risk_row else "Moderate",
        "top_risk_factors":  _json_field(risk_row, "top_risk_factors", []),
        "shap_contributions": _json_field(risk_row, "shap_contributions", {}),
    }

    simulation_result: Dict = {
        "scenarios":               _json_field(simulation_row, "scenarios", {}),
        "timeline_days":           _json_field(simulation_row, "timeline_days", []),
        "projected_risk_reduction": _json_field(simulation_row, "projected_risk_reduction", {}),
    }

    causal_result: Dict = {
        "ranked_factors": _json_field(causal_row, "ranked_factors", []),
        "primary_cause":  causal_row["primary_cause"] if causal_row else "",
        "causal_chain":   causal_row["causal_chain"]  if causal_row else "",
    }

    user_doc: Dict = dict(user_row) if user_row else {}

    shap_result = {"shap_contributions": risk_result["shap_contributions"]}

    # mem0 context
    mem_ctx     = await get_user_context(
        user_id,
        query="health risk factors recommendations sleep stress steps diet",
    )
    memory_text = format_context_for_llm(mem_ctx)

    # Try Groq
    recommendations = []
    method          = "fallback"

    if settings.groq_api_key:
        try:
            client = _get_client()
            system = _build_system_prompt()
            user_prompt = _build_user_prompt(
                user_profile      = user_doc,
                risk_result       = risk_result,
                shap_result       = shap_result,
                causal_result     = causal_result,
                simulation_result = simulation_result,
                memory_context    = memory_text,
            )

            response = await client.chat.completions.create(
                model       = settings.groq_model,
                messages    = [
                    {"role": "system",  "content": system},
                    {"role": "user",    "content": user_prompt},
                ],
                temperature = 0.3,
                max_tokens  = 1200,
            )

            raw = response.choices[0].message.content
            recommendations = _parse_recommendations(raw)
            method          = f"groq:{settings.groq_model}"

        except Exception as e:
            print(f"[recommendation_service] Groq failed: {e} — using fallback")
            recommendations = _fallback_recommendations(risk_result, causal_result)
    else:
        recommendations = _fallback_recommendations(risk_result, causal_result)

    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO recommendations (user_id, log_id, method, risk_score, recommendations, generated_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id,
            log_id,
            method,
            float(risk_result.get("risk_score", 50)),
            json.dumps(recommendations),   # JSONB → serialise
            now,
        )

    return {
        "user_id":         user_id,
        "log_id":          log_id,
        "generated_at":    now,
        "method":          method,
        "risk_score":      risk_result.get("risk_score", 50),
        "recommendations": recommendations,
    }
