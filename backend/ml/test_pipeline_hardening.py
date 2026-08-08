"""
Bug-fix verification: COR-1 (duplicate anomalies), COR-5 (KeyError), pdfplumber,
per-stage pipeline isolation.

Run: PYTHONPATH=. /opt/anaconda3/envs/darpanai/bin/python3 backend/ml/test_pipeline_hardening.py
"""

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import inspect

from backend.services import anomaly_service as A
from backend.routes import health_data as H

passed = failed = 0


def ok(label, cond):
    global passed, failed
    passed, failed = passed + bool(cond), failed + (not cond)
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")


print("\n1. COR-5 — unguarded SEVERITY_RANK lookup")
bogus = [{"metric": "heart_rate", "observed_value": 200, "expected_range": {},
          "deviation_pct": 10, "severity": "catastrophic", "layer": "rule", "message": "x"}]
try:
    out = A._merge_anomalies(bogus, [], [])
    ok("bogus severity does not raise", True)
    ok("bogus severity still returned", len(out) == 1 and out[0]["metric"] == "heart_rate")
except Exception as e:
    ok(f"bogus severity does not raise (raised {type(e).__name__})", False)

# Mixed valid + bogus severities must still sort sanely (valid ranked above unknown)
mixed = [
    {"metric": "sleep", "observed_value": 2, "expected_range": {}, "deviation_pct": 5,
     "severity": "critical", "layer": "rule", "message": "x"},
    {"metric": "steps", "observed_value": 100, "expected_range": {}, "deviation_pct": 5,
     "severity": "unknown_severity", "layer": "rule", "message": "x"},
]
out2 = A._merge_anomalies(mixed, [], [])
ok("known severity ranks above unknown", out2[0]["metric"] == "sleep")

print("\n2. COR-1 — detect_anomalies is called exactly once per submission")
route_src = inspect.getsource(H.submit_health_data)
pipeline_src_early = inspect.getsource(H.run_full_pipeline)
ok("the route calls detect_anomalies exactly once",
   route_src.count("await detect_anomalies(") == 1)
ok("run_full_pipeline only recomputes anomalies when none were passed in "
   "(defensive fallback for other callers, not the normal submission path)",
   "if anomalies is None:" in pipeline_src_early)
sig = inspect.signature(H.run_full_pipeline)
ok("run_full_pipeline accepts precomputed anomalies",
   "anomalies" in sig.parameters)
ok("submit_health_data passes anomalies into the background task",
   "anomalies,\n    )" in route_src)

print("\n3. pdfplumber install + honest failure mode")
try:
    import pdfplumber
    ok(f"pdfplumber importable (v{pdfplumber.__version__})", True)
except ImportError:
    ok("pdfplumber importable", False)

import torch
ok(f"torch still imports (v{torch.__version__})", True)

from backend.services import doc_rag_service as D
extract_src = inspect.getsource(D._extract_pdf)
ok("_extract_pdf catches ImportError with a named fix",
   "except ImportError" in extract_src and "pip install pdfplumber" in extract_src)

print("\n4. Pipeline hardening — per-stage isolation and honest status")
ok("pipeline_status endpoint exists",
   any("pipeline-status" in r.path for r in H.router.routes))
ok("in-process status store is capped (non-durable, documented)",
   H._PIPELINE_STATUS_CAP == 50)

# Simulate stage recording directly (no DB / network needed)
H._PIPELINE_STATUS.clear()
H._record_stage("log_test", "risk", True, None, 12.3)
H._record_stage("log_test", "explain", False, "boom", 1.1)
entry = H._PIPELINE_STATUS["log_test"]
ok("records both ok and failed stages", entry["stages"]["risk"]["ok"] is True
   and entry["stages"]["explain"]["ok"] is False)
ok("captures the error string", entry["stages"]["explain"]["error"] == "boom")

# Eviction: cap must actually evict oldest first
H._PIPELINE_STATUS.clear()
for i in range(H._PIPELINE_STATUS_CAP + 5):
    H._record_stage(f"log_{i}", "risk", True, None, 1.0)
ok("evicts down to the cap", len(H._PIPELINE_STATUS) == H._PIPELINE_STATUS_CAP)
ok("evicted the oldest, not the newest",
   "log_0" not in H._PIPELINE_STATUS and f"log_{H._PIPELINE_STATUS_CAP + 4}" in H._PIPELINE_STATUS)

pipeline_src = inspect.getsource(H.run_full_pipeline)
ok("each of the 6 stages is independently try/excepted",
   pipeline_src.count("except Exception as e:") >= 5)
ok("dependent stages are skipped, not run on garbage, when risk fails",
   "skipped: risk stage did not complete" in pipeline_src)
ok("stage failures are printed with a clear prefix",
   "[pipeline]" in pipeline_src)

print(f"\n{'='*58}\n  {passed} passed, {failed} failed\n{'='*58}")
raise SystemExit(1 if failed else 0)
