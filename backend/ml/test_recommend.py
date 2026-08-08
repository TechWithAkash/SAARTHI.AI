"""
Recommendation engine smoke test — no API key or MongoDB required.
Tests: prompt building, JSON parsing, fallback logic, output schema.
Run: source .venv/bin/activate && python -m backend.ml.test_recommend
"""
import json
import sys

from backend.services.recommendation_service import (
    _build_system_prompt,
    _build_user_prompt,
    _parse_recommendations,
    _fallback_recommendations,
)

SEP  = "─" * 68
PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    icon = "✓" if condition else "✗"
    print(f"  {icon} {label}" + (f"  [{detail}]" if detail else ""))
    if condition:
        PASS += 1
    else:
        FAIL += 1


# ── Fixtures ──────────────────────────────────────────────────────────────────

USER_PROFILE = {
    "age": 42, "gender": "male",
    "health_goals": ["reduce_stress", "improve_sleep"],
}
RISK_RESULT = {
    "risk_score": 67.0, "risk_category": "High",
    "top_risk_factors": ["stress_level", "sleep", "bmi"],
    "shap_contributions": {
        "stress_level": 9.2, "bmi": 4.8, "sleep": 2.9,
        "steps": -3.1, "diet_score": -1.5, "heart_rate": 1.2,
    },
}
SHAP_RESULT  = {"shap_contributions": RISK_RESULT["shap_contributions"]}
CAUSAL_RESULT = {
    "ranked_factors": [
        {"factor": "stress_level", "ate": -4.7, "chain": "stress_level → heart_rate → risk_score"},
        {"factor": "steps",        "ate": -2.4, "chain": "steps → bmi & sleep → risk_score"},
        {"factor": "sleep",        "ate": -1.0, "chain": "sleep → heart_rate & diet_score → risk_score"},
        {"factor": "diet_score",   "ate": -0.9, "chain": "diet_score → bmi → risk_score"},
    ],
    "primary_cause": "stress_level",
    "causal_chain": "stress_level → heart_rate → risk_score",
}
SIMULATION_RESULT = {
    "scenarios": {
        "current":  [67, 70, 74, 78, 82],
        "improved": [67, 61, 55, 50, 46],
        "optimal":  [67, 55, 44, 36, 30],
    },
    "timeline_days": [0, 30, 60, 90, 120],
    "projected_risk_reduction": {"improved": 31.3, "optimal": 55.2},
}
MEMORY_TEXT = (
    "User's health memory (most relevant first):\n"
    "  1. On 2024-01-10, risk was 72 (High). Stress was 9/10.\n"
    "  2. After 10 days of walking 8000 steps, risk dropped from 72 to 65.\n"
    "  3. Risk trend: increasing over last 2 weeks."
)

MOCK_GROQ_RESPONSE = json.dumps([
    {
        "priority": 1,
        "action": "Practice 10-minute box breathing at 9pm daily — 4s inhale, 4s hold, 4s exhale",
        "reason": "Stress is your #1 risk driver (+9.2 pts via stress → heart rate chain). Reducing it by 1σ cuts risk ~4.7 pts.",
        "impact": "high",
        "timeframe": "1–2 weeks",
        "estimated_risk_reduction": 4.7,
    },
    {
        "priority": 2,
        "action": "Walk 8,000 steps daily — your history shows this dropped your risk 7 pts in 10 days",
        "reason": "Steps reduced your risk before (72→65). DoWhy estimates −2.4 pts per 1σ step increase.",
        "impact": "high",
        "timeframe": "2–3 weeks",
        "estimated_risk_reduction": 2.4,
    },
    {
        "priority": 3,
        "action": "Set a consistent sleep schedule: in bed by 10:30pm, 7.5h minimum",
        "reason": "Poor sleep adds +2.9 pts to your current score and worsens diet quality downstream.",
        "impact": "medium",
        "timeframe": "3 weeks",
        "estimated_risk_reduction": 1.0,
    },
])


# ── Tests ─────────────────────────────────────────────────────────────────────

print(SEP)
print("  Test 1 — System prompt content")
print(SEP)
system = _build_system_prompt()
check("Non-empty",             len(system) > 100)
check("Mentions JSON output",  "JSON" in system)
check("Mentions priority",     "priority" in system)
check("Mentions specific",     "SPECIFIC" in system or "specific" in system)
check("Contains schema",       "estimated_risk_reduction" in system)

print()
print(SEP)
print("  Test 2 — User prompt construction")
print(SEP)
prompt = _build_user_prompt(
    USER_PROFILE, RISK_RESULT, SHAP_RESULT,
    CAUSAL_RESULT, SIMULATION_RESULT, MEMORY_TEXT,
)
print(f"  Prompt length: {len(prompt)} chars")
check("Contains risk score",      "67" in prompt)
check("Contains risk category",   "High" in prompt)
check("Contains top factor",      "stress_level" in prompt)
check("Contains SHAP values",     "+9.2" in prompt or "9.2" in prompt)
check("Contains causal ATE",      "-4.7" in prompt or "4.7" in prompt)
check("Contains simulation day30","61" in prompt)
check("Contains memory",          "walking 8000" in prompt or "8000" in prompt)
check("Contains user age",        "42" in prompt)
check("Contains goals",           "reduce_stress" in prompt or "sleep" in prompt)

print()
print(SEP)
print("  Test 3 — JSON parser: clean response")
print(SEP)
recs = _parse_recommendations(MOCK_GROQ_RESPONSE)
check("Returns list",             isinstance(recs, list))
check("3 recommendations",        len(recs) == 3)
check("Sorted by priority",       recs[0]["priority"] < recs[1]["priority"])
check("Priority 1 is stress",     "stress" in recs[0]["action"].lower() or "breath" in recs[0]["action"].lower())
check("Impact is valid enum",     all(r["impact"] in ("high","medium","low") for r in recs))
check("Risk reduction is float",  all(isinstance(r["estimated_risk_reduction"], float) for r in recs))

print()
print(SEP)
print("  Test 4 — JSON parser: response wrapped in markdown fences")
print(SEP)
wrapped = f"```json\n{MOCK_GROQ_RESPONSE}\n```"
recs_wrapped = _parse_recommendations(wrapped)
check("Handles markdown fences",  len(recs_wrapped) == 3)

with_preamble = f"Here are your recommendations:\n\n{MOCK_GROQ_RESPONSE}"
recs_preamble = _parse_recommendations(with_preamble)
check("Handles preamble text",    len(recs_preamble) == 3)

print()
print(SEP)
print("  Test 5 — Fallback recommendations (no API key)")
print(SEP)
fallback = _fallback_recommendations(RISK_RESULT, CAUSAL_RESULT)
check("Returns list",             isinstance(fallback, list))
check("At least 3 recs",         len(fallback) >= 3)
check("Priority 1 is stress",    "stress" in fallback[0]["action"].lower() or
                                  "breath" in fallback[0]["action"].lower() or
                                  fallback[0]["factor"] == "stress_level" if hasattr(fallback[0], 'get') else True)
check("All have required keys",  all(
    all(k in r for k in ["priority","action","reason","impact","timeframe","estimated_risk_reduction"])
    for r in fallback
))
check("Sorted by priority",      all(fallback[i]["priority"] <= fallback[i+1]["priority"]
                                     for i in range(len(fallback)-1)))
print()
print("  Fallback recommendations:")
for r in fallback:
    print(f"  {r['priority']}. [{r['impact'].upper()}] {r['action']}")
    print(f"     Why: {r['reason']}")
    print(f"     Timeframe: {r['timeframe']} | Est. reduction: {r['estimated_risk_reduction']:.1f} pts")

print()
print(SEP)
print("  Test 6 — Parser rejects invalid JSON gracefully")
print(SEP)
try:
    _parse_recommendations("This is not JSON at all.")
    check("Raises on bad input", False, "should have raised")
except (ValueError, Exception):
    check("Raises ValueError on bad input", True)

print()
print(SEP)
total = PASS + FAIL
print(f"  Results: {PASS} passed, {FAIL} failed out of {total} checks")
if FAIL == 0:
    print("  All recommendation tests passed ✓")
else:
    print(f"  {FAIL} check(s) failed ✗")
print(SEP)
sys.exit(0 if FAIL == 0 else 1)
