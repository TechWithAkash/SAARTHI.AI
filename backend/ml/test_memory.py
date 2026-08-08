"""
Memory service smoke test — validates text formatting and mem0 vector store.
Tests the formatters and context builder without requiring a real API key.
Run: source .venv/bin/activate && python -m backend.ml.test_memory
"""
import sys
import warnings
warnings.filterwarnings("ignore")

from datetime import datetime, timezone
from backend.services.memory_service import (
    _format_health_observation,
    _format_risk_trend,
    _format_causal_insight,
    _format_intervention_response,
    format_context_for_llm,
    _fallback_context,
)

SEP  = "─" * 68
PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    status = "✓" if condition else "✗"
    print(f"  {status} {label}" + (f" — {detail}" if detail else ""))
    if condition:
        PASS += 1
    else:
        FAIL += 1


print(SEP)
print("  Test 1 — Health observation formatter")
print(SEP)

ts = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)

obs_poor = _format_health_observation(
    {"heart_rate": 92, "sleep": 5.0, "steps": 3500,
     "stress_level": 8, "diet_score": 4, "bmi": 29.5},
    risk_score=67.0, risk_category="High", timestamp=ts,
)
print(f"  Output: {obs_poor}")
check("Contains date",          "2024-01-15" in obs_poor)
check("Contains risk score",    "67" in obs_poor)
check("Sleep labelled poor",    "poor" in obs_poor)
check("Steps labelled sedentary", "sedentary" in obs_poor)
check("Stress labelled high",   "high" in obs_poor)

print()
obs_good = _format_health_observation(
    {"heart_rate": 62, "sleep": 8.0, "steps": 9500,
     "stress_level": 2, "diet_score": 8, "bmi": 22.5},
    risk_score=24.0, risk_category="Low", timestamp=ts,
)
check("Good sleep labelled good", "good" in obs_good)
check("Steps labelled active",    "active" in obs_good)
check("Stress labelled low",      "low" in obs_good)

print()
print(SEP)
print("  Test 2 — Risk trend formatter")
print(SEP)

trend_up = _format_risk_trend(78.0, [65.0, 63.0, 61.0], "High")
print(f"  Increasing trend: {trend_up}")
check("Detects increasing trend",   trend_up is not None and "increasing" in trend_up)

trend_down = _format_risk_trend(45.0, [60.0, 62.0, 61.0], "Moderate")
print(f"  Decreasing trend: {trend_down}")
check("Detects decreasing trend",   trend_down is not None and "decreasing" in trend_down)

trend_flat = _format_risk_trend(50.0, [51.0, 49.0, 50.0], "Moderate")
check("Stable trend returns None",  trend_flat is None)

trend_few = _format_risk_trend(50.0, [49.0], "Moderate")
check("Too few readings returns None", trend_few is None)

print()
print(SEP)
print("  Test 3 — Causal insight formatter")
print(SEP)

shap = {"stress_level": 9.2, "bmi": 4.8, "sleep": 2.9, "steps": -3.1, "diet_score": -1.5}
causal = _format_causal_insight(
    primary_cause="stress_level",
    causal_chain="stress_level → heart_rate → risk_score",
    shap_contributions=shap,
)
print(f"  Output: {causal}")
check("Contains primary cause",    "stress_level" in causal)
check("Contains causal chain",     "heart_rate" in causal)
check("Lists top factors",         "9.2" in causal or "stress_level" in causal)
check("Only positive SHAP listed", "steps" not in causal and "diet_score" not in causal)

print()
print(SEP)
print("  Test 4 — Intervention response formatter")
print(SEP)

resp_good = _format_intervention_response("sleep", 67.0, 52.0, 14)
print(f"  Positive response: {resp_good}")
check("Positive response not None",     resp_good is not None)
check("Contains improved",              resp_good and "improved" in resp_good)
check("Contains days",                  resp_good and "14" in resp_good)

resp_small = _format_intervention_response("diet_score", 50.0, 49.5, 7)
check("Tiny change returns None",       resp_small is None)

resp_worse = _format_intervention_response("steps", 40.0, 48.0, 10)
print(f"  Worsened response: {resp_worse}")
check("Worsened response not None",     resp_worse is not None)
check("Contains worsened",              resp_worse and "worsened" in resp_worse)

print()
print(SEP)
print("  Test 5 — Context formatter for LLM")
print(SEP)

ctx_empty = _fallback_context("usr_001")
llm_text_empty = format_context_for_llm(ctx_empty)
check("Empty context graceful",    "No prior" in llm_text_empty)

ctx_with_memories = {
    "user_id": "usr_001",
    "memories": [
        {"text": "User's sleep dropped to 4h on 2024-01-14.", "score": 0.92},
        {"text": "Risk score increased by 8 pts over the last week.", "score": 0.87},
    ],
    "source": "mem0",
    "count": 2,
}
llm_text = format_context_for_llm(ctx_with_memories)
print(f"  LLM context:\n{llm_text}")
check("Contains memory count",     "1." in llm_text and "2." in llm_text)
check("Contains sleep memory",     "sleep" in llm_text)
check("Contains risk memory",      "Risk score" in llm_text)

print()
print(SEP)
print("  Test 6 — mem0 vector store (embedder only, no LLM needed)")
print(SEP)

try:
    from mem0 import Memory
    import tempfile, os

    tmpdir = tempfile.mkdtemp()
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "test_smoke",
                "embedding_model_dims": 384,
                "on_disk": True,
                "path": tmpdir,
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {"model": "multi-qa-MiniLM-L6-cos-v1"},
        },
        "llm": {
            "provider": "anthropic",
            "config": {"model": "claude-haiku-4-5-20251001", "api_key": "sk-dummy"},
        },
    }
    m = Memory.from_config(config)

    # add() will fail at LLM extraction — that's fine, vector store is live
    try:
        m.add([{"role": "user", "content": "User sleeps 5 hours and has high stress."}],
              user_id="test_user")
    except Exception:
        pass  # LLM auth failure expected with dummy key

    # search() uses embedder only — should work
    results = m.search("sleep stress", filters={"user_id": "test_user"}, limit=5)
    check("Vector store initialised", True, f"qdrant at {tmpdir}")
    check("Search returns list/dict",  isinstance(results, (list, dict)))

except Exception as e:
    check("mem0 vector store", False, str(e))

print()
print(SEP)
total = PASS + FAIL
print(f"  Results: {PASS} passed, {FAIL} failed out of {total} checks")
if FAIL == 0:
    print("  All memory tests passed ✓")
else:
    print(f"  {FAIL} check(s) failed ✗")
print(SEP)
sys.exit(0 if FAIL == 0 else 1)
