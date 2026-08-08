"""
Block D tests — causal ATE grounding, estimator honesty, agent anti-drift.

The central assertion: `estimated_risk_reduction` can no longer originate from
the LLM. Every value is either derived from causal_service's measured effect, or
absent. No Groq calls are made — the LLM step is stubbed.

Run: PYTHONPATH=. /opt/anaconda3/envs/darpanai/bin/python3 backend/ml/test_causal_ate.py
"""

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import asyncio
import inspect

from backend.services import causal_service as CS
from backend.services import cognitive_agent_service as AG

passed = failed = 0


def check(label, got, expected):
    global passed, failed
    ok_ = got == expected
    passed, failed = passed + ok_, failed + (not ok_)
    print(f"  {'PASS' if ok_ else 'FAIL'}  {label}: got={got!r} expected={expected!r}")


def ok(label, cond):
    global passed, failed
    passed, failed = passed + bool(cond), failed + (not cond)
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")


# Realistic ranked_factors as causal_service now emits them
FACTORS = [
    {"factor": "stress_level", "ate": -4.2, "chain": "stress_level -> heart_rate -> risk_score", "estimator": "dowhy_backdoor"},
    {"factor": "sleep",        "ate": -2.8, "chain": "sleep -> heart_rate",                      "estimator": "dowhy_backdoor"},
    {"factor": "steps",        "ate": -1.5, "chain": "steps -> bmi",                             "estimator": "linear_backdoor"},
    {"factor": "diet_score",   "ate": -0.9, "chain": "diet_score -> bmi",                        "estimator": "dowhy_backdoor"},
    {"factor": "bmi",          "ate": -3.1, "chain": "bmi -> heart_rate",                        "estimator": "dowhy_backdoor"},
]

print("\n1. _attribute_factor maps free-text recommendations to causal factors")
cases = [
    ("stress", {"action": "Practise 10 minutes of box breathing before bed",
                "reason": "Your cortisol-driven stress is the top driver",
                "causal_mechanism": "lowers cortisol"}, "stress_level"),
    ("sleep",  {"action": "Move bedtime 45 minutes earlier",
                "reason": "You average 5.2h; insomnia raises resting HR",
                "causal_mechanism": "restores circadian rhythm"}, "sleep"),
    ("steps",  {"action": "Walk 8,000 steps before 9 PM",
                "reason": "You are sedentary at 3,200 steps/day",
                "causal_mechanism": "activity reduces BMI"}, "steps"),
    ("diet",   {"action": "Replace one processed meal with whole foods",
                "reason": "High sugar intake drives glycaemic load",
                "causal_mechanism": "reduces sugar"}, "diet_score"),
    ("bmi",    {"action": "Target a 0.5 BMI reduction per month",
                "reason": "Central adiposity at waist 97cm",
                "causal_mechanism": "weight loss lowers resting HR"}, "bmi"),
]
for label, rec, expect in cases:
    got = AG._attribute_factor(rec, FACTORS)
    check(f"{label} -> {expect}", got and got["factor"], expect)

print("\n2. Ambiguous multi-match resolves to the largest |ate|")
# Mentions walking AND diet; stress_level not mentioned. steps=-1.5, diet=-0.9
amb = {"action": "Take a walk after dinner instead of dessert",
       "reason": "combines activity with a better food choice", "causal_mechanism": ""}
m = AG._attribute_factor(amb, FACTORS)
ok("picked the stronger lever (steps over diet)", m and m["factor"] == "steps")

print("\n3. No keyword match -> no number at all")
nomatch = {"action": "Schedule an annual physical with your physician",
           "reason": "Routine screening is prudent", "causal_mechanism": ""}
check("returns None", AG._attribute_factor(nomatch, FACTORS), None)
grounded = AG._ground_risk_reductions([dict(nomatch)], None)
check("estimated_risk_reduction is None", grounded[0]["estimated_risk_reduction"], None)
check("source is unavailable", grounded[0]["risk_reduction_source"], "unavailable")

print("\n4. LLM-invented numbers are DISCARDED (the BP-3 fix)")


class FakeRow(dict):
    """Stands in for an asyncpg Record."""
    def __getitem__(self, k):
        return dict.get(self, k)


causal_row = FakeRow(ranked_factors=FACTORS, primary_cause="stress_level")

# The LLM tries to assert 99.9 points of benefit on every recommendation.
llm_output = [
    {"priority": 1, "action": "Practise breathing exercises to cut stress",
     "reason": "stress is your driver", "causal_mechanism": "lowers cortisol",
     "estimated_risk_reduction": 99.9},
    {"priority": 2, "action": "Walk 10,000 steps daily",
     "reason": "sedentary", "causal_mechanism": "", "estimated_risk_reduction": 88.8},
    {"priority": 3, "action": "See a doctor sometime",
     "reason": "general", "causal_mechanism": "", "estimated_risk_reduction": 77.7},
]
out = AG._ground_risk_reductions([dict(r) for r in llm_output], causal_row)

check("stress rec uses real ATE 4.2",  out[0]["estimated_risk_reduction"], 4.2)
check("stress rec labelled causal_ate", out[0]["risk_reduction_source"], "causal_ate")
check("steps rec uses real ATE 1.5",   out[1]["estimated_risk_reduction"], 1.5)
check("steps estimator recorded",      out[1]["causal_estimator"], "linear_backdoor")
check("unmatched rec shows no number",  out[2]["estimated_risk_reduction"], None)
ok("NO fabricated value survived anywhere",
   not any(r.get("estimated_risk_reduction") in (99.9, 88.8, 77.7) for r in out))

print("\n5. SHAP priors are not passed off as causal effects")
shap_factors = [{"factor": "stress_level", "ate": -2.0, "chain": "", "estimator": "shap_prior"}]
srow = FakeRow(ranked_factors=shap_factors, primary_cause="stress_level")
sout = AG._ground_risk_reductions(
    [{"action": "Reduce stress with meditation", "reason": "", "causal_mechanism": ""}], srow)
check("labelled shap_prior, not causal_ate", sout[0]["risk_reduction_source"], "shap_prior")
ok("value still present but weaker-labelled", sout[0]["estimated_risk_reduction"] == 2.0)

print("\n6. The prompt no longer invites the model to invent a number")
src = inspect.getsource(AG._step_recommendation_engine)
ok('example no longer shows "estimated_risk_reduction": 3.2', '": 3.2' not in src)
ok("prompt sets the field to null", '"estimated_risk_reduction": null' in src)
ok("prompt forbids estimating", "do NOT estimate any numeric risk reduction" in src)
ok("grounding is applied after parsing", "_ground_risk_reductions" in src)

print("\n7. ARC-3: one pipeline, no drift")
ok("shared _run_pipeline exists", hasattr(AG, "_run_pipeline"))
stream_src = inspect.getsource(AG.stream_cognitive_agent)
sync_src = inspect.getsource(AG.run_cognitive_agent)
for name in ("_step_risk_analyst", "_step_memory_agent",
             "_step_causal_strategist", "_step_recommendation_engine"):
    ok(f"stream does not re-call {name}", name not in stream_src)
    ok(f"sync does not re-call {name}", name not in sync_src)
ok("both consume _run_pipeline",
   "_run_pipeline" in stream_src and "_run_pipeline" in sync_src)

print("\n8. n_tool_calls is derived, not hardcoded")
check("4 tools listed", len(AG.TOOLS_CALLED), 4)
pipeline_src = inspect.getsource(AG._run_pipeline)
ok("uses len(TOOLS_CALLED)", "len(TOOLS_CALLED)" in pipeline_src)
ok('no literal "n_tool_calls": 3', '"n_tool_calls": 3' not in pipeline_src)
ok("all 4 steps declared in STEP_META", len(AG.STEP_META) == 4)

print("\n9. BP-4: estimator labels reflect what actually ran")
ok("MIN_HISTORY_ATE raised to 14", CS.MIN_HISTORY_ATE == 14)
ok("MIN_HISTORY_ATE exceeds predictor count",
   CS.MIN_HISTORY_ATE > len(CS.TREATMENTS) + 2)
dowhy_src = inspect.getsource(CS._estimate_with_dowhy)
ok("returns (ate, estimator) tuple", "-> tuple[Optional[float], str]" in dowhy_src)
ok("labels its linear fallback distinctly", '"linear_backdoor"' in dowhy_src)
ok("logs dowhy failure instead of swallowing", "[causal] dowhy failed" in dowhy_src)

persist_src = inspect.getsource(CS._persist_causal)
ok("method derived from actual estimators", '"mixed"' in persist_src)
ok("no unconditional dowhy_backdoor label",
   'if df is not None and len(df) >= MIN_HISTORY else "shap_prior"' not in persist_src)
ok("exposes is_causal flag", '"is_causal"' in persist_src)

print("\n10. Degenerate regressions are refused")
import pandas as pd
tiny = pd.DataFrame({
    "risk_score":   [40.0, 41.0, 39.0],
    "stress_level": [7.0, 8.0, 6.0],
    "sleep":        [5.0, 5.5, 6.0],
    "steps":        [3000.0, 3200.0, 2800.0],
    "diet_score":   [3.0, 4.0, 3.5],
    "bmi":          [29.0, 29.1, 29.2],
})
check("3 rows, 5 predictors -> None", CS._estimate_ate_linear(tiny, "stress_level"), None)

print(f"\n{'='*58}\n  {passed} passed, {failed} failed\n{'='*58}")
raise SystemExit(1 if failed else 0)
