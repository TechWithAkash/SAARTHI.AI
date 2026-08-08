"""
Garmin adapter tests — field extraction, scale conversion, safety guards.

These deliberately never touch the network. A real Garmin login cannot be part
of a test suite: the account is rate-limited and repeated failures get the
source IP temporarily blocked. So we test the part that actually breaks in
practice — parsing real-shaped JSON whose keys vary by device and firmware.

Run: /opt/anaconda3/envs/darpanai/bin/python3 backend/ml/test_garmin.py
"""

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

from pathlib import Path

from backend.services import garmin_service as G

passed = failed = 0


def check(label, got, expected):
    global passed, failed
    ok = got == expected
    passed, failed = passed + ok, failed + (not ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: got={got!r} expected={expected!r}")


# ── Realistic payloads, shaped like Garmin's actual responses ────────────────

STATS = {
    "totalSteps": 8423,
    "restingHeartRate": 58,
    "averageStressLevel": 34,
    "sleepingSeconds": 25200,
}
SLEEP = {"dailySleepDTO": {"sleepTimeSeconds": 26100, "deepSleepSeconds": 5400}}
HRV = {"hrvSummary": {"lastNightAvg": 42, "weeklyAvg": 38}}
STRESS = {"avgStressLevel": 34, "maxStressLevel": 91}
BODY = {"dateWeightList": [{"weight": 78500, "bmi": 26.1}]}
SPO2 = {"averageSpO2": 96}
BB_ROW = {"date": "2026-08-08", "charged": 61, "drained": 48}
STEPS_ROW = {"calendarDate": "2026-08-08", "totalSteps": 9111}

print("\n1. Extraction from well-formed payloads")
check("steps",        G._extract_steps(STATS),                    8423.0)
check("resting HR",   G._extract_resting_hr(STATS),               58.0)
check("sleep hours",  G._extract_sleep_hours(SLEEP, STATS),       7.25)
check("HRV RMSSD",    G._extract_hrv_rmssd(HRV),                  42.0)
check("spo2",         G._extract_spo2(SPO2),                      96.0)
check("bmi/weight",   G._extract_bmi(BODY),                       (26.1, 78.5))
check("body battery", G._extract_body_battery(BB_ROW),
      {"body_battery_charged": 61.0, "body_battery_drained": 48.0})
check("steps (range row)", G._extract_steps(None, STEPS_ROW),     9111.0)

print("\n2. Stress 0-100 -> app 1-10 (linear, 1 + g/100*9)")
for g, exp in [(0, 1.0), (34, 4.06), (50, 5.5), (100, 10.0)]:
    check(f"garmin {g}", G.garmin_stress_to_app_scale(g), exp)
check("sentinel -1 -> None", G.garmin_stress_to_app_scale(-1), None)
check("None -> None",        G.garmin_stress_to_app_scale(None), None)

print("\n3. Every key missing -> None, never an exception")
check("steps",      G._extract_steps({}),              None)
check("resting HR", G._extract_resting_hr({}),         None)
check("sleep",      G._extract_sleep_hours({}, {}),    None)
check("HRV",        G._extract_hrv_rmssd({}),          None)
check("spo2",       G._extract_spo2({}),               None)
check("bmi",        G._extract_bmi({}),                (None, None))
check("stress",     G._extract_stress({}, {}),         None)

print("\n4. Junk / hostile payloads do not raise")
for bad in (None, [], "garbage", 42, {"dailySleepDTO": None}, {"hrvSummary": "x"}):
    try:
        G._extract_steps(bad); G._extract_sleep_hours(bad, bad)
        G._extract_hrv_rmssd(bad); G._extract_bmi(bad)
        print(f"  PASS  survived {bad!r}")
        passed += 1
    except Exception as e:
        print(f"  FAIL  raised on {bad!r}: {type(e).__name__}: {e}")
        failed += 1

print("\n5. Implausible values rejected rather than trusted")
check("RMSSD 999 (out of band)", G._extract_hrv_rmssd({"hrvSummary": {"lastNightAvg": 999}}), None)
check("sleep 40h (sentinel)",    G._extract_sleep_hours({"sleepTimeSeconds": 144000}, None),  None)
check("bmi 200",                 G._extract_bmi({"bmi": 200})[0],                             None)

print("\n6. Safety guards")
from backend.config import settings
check("diet_score declared unavailable", "diet_score" in G.UNAVAILABLE_FROM_GARMIN, True)

# IMPORTANT: this whole block runs with fully MOCKED config/token-store state,
# regardless of what's actually in .env or on disk in this environment.
#
# Why: _login_sync() checks for a cached token file BEFORE it even checks
# whether credentials are configured — so once real credentials and a real
# cached token exist on this machine (as they now do), calling the real
# function with real settings resumes a REAL session. That happened once
# during development of this test: a naive version of this check ran against
# a real .env with real cached tokens and silently exercised the live
# resume path instead of the "not configured" path it meant to test. Never
# let a login-adjacent test run against the ambient real environment again —
# override BOTH garmin_configured and garmin_token_store for the duration.
_orig_configured = type(settings).garmin_configured
_orig_store = settings.garmin_token_store
try:
    type(settings).garmin_configured = property(lambda self: False)
    settings.garmin_token_store = "/tmp/__nonexistent_garmin_tokens_for_test__"

    check("mocked-unconfigured state is actually unconfigured (sanity check)",
          settings.garmin_configured, False)
    check("mocked token store path does not exist (sanity check)",
          Path(settings.garmin_token_store).exists(), False)

    G._client, G._login_attempts, G._login_blocked = None, 0, False
    try:
        G._login_sync()
        print("  FAIL  login attempted with placeholder/mocked credentials")
        failed += 1
    except G.GarminUnavailable as e:
        print(f"  PASS  refused to attempt login: {str(e)[:60]}...")
        passed += 1
    check("no attempt consumed", G._login_attempts, 0)
finally:
    # Restore, don't delete — `del` here would remove the class-level
    # property entirely (Python has no assignment history to fall back on),
    # breaking settings.garmin_configured for the rest of this process. That
    # bug existed transiently while writing this fix and crashed the very
    # next test block, which reads settings.garmin_configured right after.
    type(settings).garmin_configured = _orig_configured
    settings.garmin_token_store = _orig_store
    G._client, G._login_attempts, G._login_blocked = None, 0, False

# The 2-attempt cap must latch permanently.
# Also isolates garmin_token_store to a nonexistent path, same reasoning as
# the block above — without it, this would resume the REAL cached session
# before ever reaching the credentials path this test means to exercise.
import backend.services.garmin_service as GS
GS._client, GS._login_attempts, GS._login_blocked = None, 0, False
_orig_configured2 = type(settings).garmin_configured
_orig_store2 = settings.garmin_token_store
try:
    type(settings).garmin_configured = property(lambda self: True)
    settings.garmin_token_store = "/tmp/__nonexistent_garmin_tokens_for_test__"
    import garminconnect
    orig_cls = garminconnect.Garmin

    class Boom:
        def __init__(self, **kw): pass
        def login(self, *a): raise RuntimeError("bad credentials")
    garminconnect.Garmin = Boom

    for i in range(4):
        GS._client = None
        try:
            GS._login_sync()
        except GS.GarminUnavailable:
            pass
    check("attempts capped at max", GS._login_attempts, settings.garmin_max_login_attempts)
    check("login latched blocked", GS._login_blocked, True)
    garminconnect.Garmin = orig_cls
finally:
    type(settings).garmin_configured = _orig_configured2
    settings.garmin_token_store = _orig_store2

print(f"\n{'='*58}\n  {passed} passed, {failed} failed\n{'='*58}")
raise SystemExit(1 if failed else 0)
