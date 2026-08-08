"""
Air-quality service tests — CPCB conversion, fallback safety, isolation.

No network access. The critical assertion here is the LAST one: nothing this
module produces can reach the risk model.

Run: PYTHONPATH=. /opt/anaconda3/envs/darpanai/bin/python3 backend/ml/test_air_quality.py
"""

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import asyncio
import inspect

from backend.services import air_quality_service as AQ

passed = failed = 0


def check(label, got, expected):
    global passed, failed
    ok = got == expected
    passed, failed = passed + ok, failed + (not ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got={got!r} expected={expected!r}")


def ok(label, cond):
    global passed, failed
    passed, failed = passed + bool(cond), failed + (not cond)
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")


print("\n1. CPCB PM2.5 -> AQI at band boundaries")
# Each CPCB band maps piecewise-linearly onto its AQI range.
for pm25, exp_aqi, exp_cat in [
    (0.0,   0,   "Good"),
    (30.0,  50,  "Good"),            # top of Good
    (60.0,  100, "Satisfactory"),    # top of Satisfactory
    (90.0,  200, "Moderate"),        # top of Moderate
    (120.0, 300, "Poor"),            # top of Poor
    (250.0, 400, "Very Poor"),       # top of Very Poor
    (380.0, 500, "Severe"),          # top of scale
]:
    check(f"pm25={pm25:g}", AQ.pm25_to_aqi(pm25), (exp_aqi, exp_cat))

print("\n2. Midpoints interpolate, not round to a band edge")
# 45 ug/m3 sits mid-Satisfactory: (100-51)/(60-30)*(45-30)+51 = 75.5 -> 76
check("pm25=45 (mid Satisfactory)", AQ.pm25_to_aqi(45.0), (76, "Satisfactory"))
# 75 sits mid-Moderate: (200-101)/(90-60)*(75-60)+101 = 150.5, and Python's
# round() is banker's rounding, so 150.5 -> 150.
check("pm25=75 (mid Moderate)",     AQ.pm25_to_aqi(75.0), (150, "Moderate"))

print("\n3. Out-of-range inputs clamp instead of raising")
check("pm25=600 clamps to 500", AQ.pm25_to_aqi(600.0), (500, "Severe"))
check("pm25=-5 floors at 0",    AQ.pm25_to_aqi(-5.0),  (0,   "Good"))

print("\n4. AQI is monotonically non-decreasing in PM2.5")
vals = [AQ.pm25_to_aqi(p)[0] for p in range(0, 400, 5)]
ok("monotonic across 0-400", all(a <= b for a, b in zip(vals, vals[1:])))

print("\n5. Advisory content and framing")
adv = AQ.cvd_advisory(100.0)
check("category at 100 ug/m3", adv["category"], "Poor")
check("20x WHO annual guideline", adv["times_who_annual_guideline"], 20.0)
ok("carries not_included_in_risk_score", adv["not_included_in_risk_score"] is True)
ok("cites Hoek et al.", "Hoek" in adv["citation"])
ok("cites WHO guidelines", "WHO" in adv["citation"])
ok("states uncertainty / CI", "CI" in adv["uncertainty"])
ok("frames as POPULATION level", "POPULATION" in adv["population_context"])
ok("says not this individual's prediction", "not a prediction" in adv["uncertainty"])
ok("has actionable guidance", len(adv["advisory"]) > 30)
ok("severe advises against outdoor exercise",
   "not exercise outdoors" in AQ.cvd_advisory(300.0)["advisory"].lower()
   or "do not exercise" in AQ.cvd_advisory(300.0)["advisory"].lower())
ok("good air imposes no constraint", "not a constraint" in AQ.cvd_advisory(10.0)["advisory"])

print("\n6. Fallback path: never crashes, and is honest about why it fell back")
from backend.config import settings
has_key = bool(settings.openaq_api_key)
print(f"  (OPENAQ_API_KEY {'is' if has_key else 'is not'} configured in this environment)")

if not has_key:
    # _fetch_openaq must short-circuit without any HTTP when unkeyed.
    res = asyncio.run(AQ._fetch_openaq("Mumbai"))
    check("unkeyed OpenAQ returns None", res, None)
else:
    # A key is configured — the short-circuit branch doesn't apply here, but
    # the function must still degrade to None on any network/parse failure
    # rather than raising, which is what the fallback path depends on.
    ok("_fetch_openaq is defined and callable with a key present",
       inspect.iscoroutinefunction(AQ._fetch_openaq))

# get_air_quality touches the DB for caching; with no DB in a test process the
# cache lookup fails and is swallowed, so we exercise the pure fallback tail.
for city, exp_pm in [("Delhi", 100.0), ("Mumbai", 45.0), ("Bengaluru", 32.0)]:
    a = AQ.cvd_advisory(AQ.STATIC_PM25[city.lower()])
    check(f"{city} baseline pm25", a["pm25"], exp_pm)

ok("unknown city falls back to national estimate",
   AQ.STATIC_PM25.get("atlantis", AQ.STATIC_DEFAULT_PM25) == AQ.STATIC_DEFAULT_PM25)
ok("bundled set covers 15+ cities", len(AQ.STATIC_PM25) >= 15)
ok("Indian metros exceed WHO annual guideline",
   all(v > AQ.WHO_ANNUAL_PM25 for v in AQ.STATIC_PM25.values()))

print("\n7. ISOLATION — nothing here may reach the risk model")
# Checked structurally via AST, not by grepping text: the module's own
# docstrings deliberately MENTION predict_risk to say it must never be called,
# so a substring search would flag its own safety documentation.
import ast

tree = ast.parse(inspect.getsource(AQ))

imported = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imported.update(a.name for a in node.names)
    elif isinstance(node, ast.ImportFrom):
        imported.add(node.module or "")
        imported.update(f"{node.module or ''}.{a.name}" for a in node.names)

for banned_mod in ("ensemble_service", "simulation_service", "risk_service", "explain_service"):
    ok(f"does not import {banned_mod}",
       not any(banned_mod in m for m in imported))

# No executable reference to a scoring function anywhere in the module body.
called_names = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Name):
        called_names.add(node.id)
    elif isinstance(node, ast.Attribute):
        called_names.add(node.attr)

for banned in ("predict_risk", "build_sequence_from_history",
               "build_sequence_from_snapshot", "simulate_overrides",
               "get_ensemble", "predict_batch"):
    ok(f"never references {banned}", banned not in called_names)

# `composite_risk` must not be assigned or read as a real symbol here.
ok("never references composite_risk as a symbol",
   "composite_risk" not in called_names)

# And the module genuinely cannot produce a modified risk score: verify the
# advisory dict's numeric fields are all air-quality quantities.
numeric_fields = {k for k, v in AQ.cvd_advisory(80.0).items() if isinstance(v, (int, float))
                  and not isinstance(v, bool)}
ok("numeric outputs are air-quality quantities only",
   numeric_fields <= {"pm25", "aqi", "who_annual_guideline", "who_24h_guideline",
                      "times_who_annual_guideline"})

# The advisory dict must not carry a key that a naive consumer could add in.
adv_keys = set(AQ.cvd_advisory(80.0))
ok("exposes no 'risk_delta'-style field",
   not any(k in adv_keys for k in ("risk_delta", "risk_increase", "adjusted_cvd_risk",
                                   "cvd_risk_adjustment", "risk_multiplier")))

print(f"\n{'='*58}\n  {passed} passed, {failed} failed\n{'='*58}")
raise SystemExit(1 if failed else 0)
