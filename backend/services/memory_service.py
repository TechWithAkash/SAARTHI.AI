"""
Memory Service — DarpanAI Phase 9.

Uses mem0 (pgvector + HuggingFace embedder + Groq LLM) to build
a persistent, searchable health memory for each user.

What gets stored:
  - Health observations: "On 2024-01-15, user had risk score 67 (High).
    Sleep was 5.5h (poor), stress was 7/10 (elevated), steps were 4200."
  - Behaviour patterns: "User consistently skips sleep on weekdays."
  - Intervention responses: "After walking 8000 steps for 5 days, risk
    dropped from 67 to 54."
  - Causal insights: "User's primary risk driver is stress → heart rate."
  - Risk trends: "Risk has been increasing over the past 2 weeks."

What gets retrieved:
  - Relevant context for the recommendation engine
  - User's historical response to specific interventions
  - Long-term trends not visible in a single snapshot

Architecture:
  - mem0 Memory object (singleton per process)
  - PostgreSQL pgvector (same DB as app — no extra service)
  - HuggingFace multi-qa-MiniLM-L6-cos-v1 embedder (384-dim, ~25MB, free)
  - Groq LLM for memory extraction (fast, low-latency)
"""

import asyncio
import os
import warnings
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

warnings.filterwarnings("ignore")

from backend.db.postgres import get_db
from backend.config import settings

# Set HF token before any HuggingFace imports so model downloads are authenticated
if settings.hf_token:
    os.environ["HF_TOKEN"] = settings.hf_token
    os.environ["HUGGINGFACE_TOKEN"] = settings.hf_token

_memory_instance = None


def _get_memory():
    """Lazy-initialise mem0 Memory singleton."""
    global _memory_instance
    if _memory_instance is not None:
        return _memory_instance

    try:
        from mem0 import Memory

        # Parse DATABASE_URL: postgresql://user:pass@host:port/dbname
        url = urllib.parse.urlparse(settings.database_url)

        config = {
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "host": url.hostname,
                    "port": url.port or 5432,
                    "dbname": url.path.lstrip("/"),
                    "user": url.username,
                    "password": url.password or "",
                    "collection_name": "health_memories",
                    "embedding_model_dims": 384,
                },
            },
            "embedder": {
                "provider": "huggingface",
                "config": {"model": "multi-qa-MiniLM-L6-cos-v1"},
            },
            "llm": {
                "provider": "groq",
                "config": {
                    # llama-3.1-8b-instant: only current small production model on Groq.
                    # We keep input truncated to ~1300 chars in chat_service so total
                    # tokens stay under 6k TPM free-tier limit.
                    "model": "llama-3.1-8b-instant",
                    "api_key": settings.groq_api_key,
                    "temperature": 0.1,
                    "max_tokens": 200,
                },
            },
        }

        _memory_instance = Memory.from_config(config)

    except Exception as e:
        # If mem0 fails to init (missing key, etc.) return None — service degrades gracefully
        print(f"[memory_service] mem0 init failed: {e} — operating without memory")
        _memory_instance = None

    return _memory_instance


# ── Text formatters ───────────────────────────────────────────────────────────

def _format_health_observation(
    health_data: dict,
    risk_score: float,
    risk_category: str,
    timestamp: datetime,
) -> str:
    date_str = timestamp.strftime("%Y-%m-%d")
    hr    = health_data.get("heart_rate", "?")
    sleep = health_data.get("sleep", "?")
    steps = int(health_data.get("steps", 0))
    stress = health_data.get("stress_level", "?")
    diet  = health_data.get("diet_score", "?")
    bmi   = health_data.get("bmi", "?")

    sleep_note  = "poor" if float(sleep) < 6 else ("good" if float(sleep) >= 7.5 else "adequate")
    stress_note = "high" if float(stress) >= 7 else ("low" if float(stress) <= 3 else "moderate")
    steps_note  = "sedentary" if steps < 4000 else ("active" if steps >= 8000 else "lightly active")

    return (
        f"On {date_str}, health check recorded: risk score {risk_score:.0f}/100 ({risk_category}). "
        f"Sleep was {sleep}h ({sleep_note}). "
        f"Stress level was {stress}/10 ({stress_note}). "
        f"Steps were {steps:,} ({steps_note}). "
        f"Heart rate {hr} bpm. Diet score {diet}/10. BMI {bmi}."
    )


def _format_risk_trend(
    current_score: float,
    previous_scores: List[float],
    current_category: str,
) -> Optional[str]:
    if len(previous_scores) < 3:
        return None

    recent_avg = sum(previous_scores[:3]) / 3
    delta = current_score - recent_avg
    direction = "increasing" if delta > 3 else ("decreasing" if delta < -3 else "stable")

    if direction == "stable":
        return None  # Not worth storing

    return (
        f"Risk trend: score is {direction} — current {current_score:.0f} vs "
        f"3-reading average {recent_avg:.0f}. Category: {current_category}."
    )


def _format_causal_insight(
    primary_cause: str,
    causal_chain: str,
    shap_contributions: dict,
) -> str:
    top_factors = sorted(
        [(k, v) for k, v in shap_contributions.items() if v > 0],
        key=lambda x: -x[1],
    )[:3]
    factors_str = ", ".join(f"{k} (+{v:.1f} pts)" for k, v in top_factors)
    return (
        f"Causal analysis: primary risk driver is {primary_cause}. "
        f"Causal chain: {causal_chain}. "
        f"Top contributing factors today: {factors_str}."
    )


def _format_intervention_response(
    factor: str,
    old_score: float,
    new_score: float,
    days_elapsed: int,
) -> Optional[str]:
    delta = old_score - new_score
    if abs(delta) < 2:
        return None  # Noise — not worth storing
    direction = "improved" if delta > 0 else "worsened"
    return (
        f"After focusing on {factor} for {days_elapsed} days, "
        f"risk score {direction} by {abs(delta):.1f} points "
        f"(from {old_score:.0f} to {new_score:.0f})."
    )


# ── Public API ────────────────────────────────────────────────────────────────

async def store_health_observation(
    user_id: str,
    health_data: dict,
    risk_score: float,
    risk_category: str,
    shap_contributions: dict,
    causal_chain: str,
    primary_cause: str,
    timestamp: Optional[datetime] = None,
) -> bool:
    mem = _get_memory()
    if mem is None:
        return False

    ts = timestamp or datetime.now(timezone.utc)

    # Build memories to store
    messages = []

    # 1. Health observation
    obs = _format_health_observation(health_data, risk_score, risk_category, ts)
    messages.append({"role": "user", "content": obs})

    # 2. Causal insight
    if shap_contributions and causal_chain:
        causal_text = _format_causal_insight(primary_cause, causal_chain, shap_contributions)
        messages.append({"role": "user", "content": causal_text})

    # 3. Risk trend (compare to history)
    pool = get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT risk_score FROM risk_scores WHERE user_id=$1 ORDER BY timestamp DESC LIMIT 5",
            user_id,
        )
    prev_scores = [r["risk_score"] for r in rows if r["risk_score"] is not None]

    trend_text = _format_risk_trend(risk_score, prev_scores, risk_category)
    if trend_text:
        messages.append({"role": "user", "content": trend_text})

    try:
        for msg in messages:
            await asyncio.to_thread(
                mem.add,
                [msg],
                user_id=user_id,
                metadata={
                    "type":      "health_observation",
                    "timestamp": ts.isoformat(),
                    "risk_score": risk_score,
                },
            )
        return True
    except Exception as e:
        print(f"[memory_service] store failed: {e}")
        return False


async def store_intervention_response(
    user_id: str,
    factor: str,
    old_score: float,
    new_score: float,
    days_elapsed: int,
) -> bool:
    mem = _get_memory()
    if mem is None:
        return False

    text = _format_intervention_response(factor, old_score, new_score, days_elapsed)
    if not text:
        return False

    try:
        await asyncio.to_thread(
            mem.add,
            [{"role": "user", "content": text}],
            user_id=user_id,
            metadata={"type": "intervention_response", "factor": factor},
        )
        return True
    except Exception as e:
        print(f"[memory_service] store_intervention failed: {e}")
        return False


async def get_user_context(
    user_id: str,
    query: str = "health risk factors and recent patterns",
    limit: int = 8,
) -> Dict[str, Any]:
    """
    Search for relevant memories for a given query.
    Returns structured context for the recommendation engine.
    """
    mem = _get_memory()

    if mem is None:
        return _fallback_context(user_id)

    try:
        results = await asyncio.to_thread(mem.search, query=query, filters={"user_id": user_id}, limit=limit)

        memories = []
        if isinstance(results, dict):
            items = results.get("results", [])
        elif isinstance(results, list):
            items = results
        else:
            items = []

        for item in items:
            if isinstance(item, dict):
                memories.append({
                    "text":     item.get("memory", item.get("text", "")),
                    "score":    item.get("score", 0.0),
                    "metadata": item.get("metadata", {}),
                })

        return {
            "user_id":  user_id,
            "memories": memories,
            "source":   "mem0",
            "count":    len(memories),
        }

    except Exception as e:
        print(f"[memory_service] search failed: {e}")
        return _fallback_context(user_id)


async def get_all_memories(user_id: str) -> List[Dict]:
    """Return all stored memories for a user (for debugging / display)."""
    mem = _get_memory()
    if mem is None:
        return []
    try:
        results = await asyncio.to_thread(mem.get_all, user_id=user_id)
        if isinstance(results, dict):
            return results.get("results", [])
        return results if isinstance(results, list) else []
    except Exception:
        return []


async def delete_user_memories(user_id: str) -> bool:
    """GDPR-style memory deletion for a user."""
    mem = _get_memory()
    if mem is None:
        return False
    try:
        await asyncio.to_thread(mem.delete_all, user_id=user_id)
        return True
    except Exception:
        return False


def _fallback_context(user_id: str) -> Dict[str, Any]:
    """Returned when mem0 is unavailable — empty but well-formed."""
    return {
        "user_id":  user_id,
        "memories": [],
        "source":   "fallback",
        "count":    0,
    }


# ── Context formatter for recommendation engine ───────────────────────────────

def format_context_for_llm(context: Dict[str, Any]) -> str:
    """
    Format mem0 results into a plain-text block for injection
    into the recommendation engine's system prompt.
    """
    memories = context.get("memories", [])
    if not memories:
        return "No prior health history available."

    lines = ["User's health memory (most relevant first):"]
    for i, mem in enumerate(memories, 1):
        text = mem.get("text", "")
        if text:
            lines.append(f"  {i}. {text}")

    return "\n".join(lines)
