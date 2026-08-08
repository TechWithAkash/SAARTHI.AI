"""
Standalone anomaly detection test — no MongoDB, no Merlion required.
Dependencies: numpy, standard library only.

Logic under test:
  - Z-score comparison of a new reading against a user's personal baseline
  - Anomaly flagged when |z| > 2.5
  - Rule-based bounds checking (heart_rate > 150 always flagged)
  - Severity: low (2.5–3σ), medium (3–4σ), high (>4σ or rule-based critical)
"""

import math
import sys

# ---------------------------------------------------------------------------
# Core detection logic (inline — no backend imports)
# ---------------------------------------------------------------------------

RULE_BASED_BOUNDS = {
    "heart_rate": {"critical_high": 150},
    "sleep":      {"critical_low": 3},
    "stress_level": {"critical_high": 9},
}

ANOMALY_THRESHOLD = 2.5  # σ


def compute_baseline(history: list[dict]) -> dict:
    """Return {metric: (mean, std)} for each metric in history."""
    if not history:
        return {}

    metrics = list(history[0].keys())
    baseline = {}
    for m in metrics:
        values = [r[m] for r in history if m in r]
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance)
        baseline[m] = (mean, std)
    return baseline


def detect_anomalies(reading: dict, baseline: dict) -> list[dict]:
    """
    Detect anomalies in *reading* given *baseline*.

    Returns a list of anomaly dicts:
        {"metric": str, "value": float, "z_score": float|None, "severity": str, "reason": str}
    """
    anomalies = []

    for metric, value in reading.items():
        z_score = None
        flagged = False
        severity = None
        reason = None

        # --- Z-score check ---
        if metric in baseline:
            mean, std = baseline[metric]
            if std > 0:
                z_score = (value - mean) / std
                abs_z = abs(z_score)
                if abs_z > ANOMALY_THRESHOLD:
                    flagged = True
                    if abs_z > 4:
                        severity = "high"
                    elif abs_z > 3:
                        severity = "medium"
                    else:
                        severity = "low"
                    reason = f"z-score={z_score:.2f} (mean={mean:.1f}, std={std:.1f})"

        # --- Rule-based bounds check (may upgrade severity) ---
        if metric in RULE_BASED_BOUNDS:
            bounds = RULE_BASED_BOUNDS[metric]
            critical_high = bounds.get("critical_high")
            critical_low  = bounds.get("critical_low")
            rule_triggered = False

            if critical_high is not None and value > critical_high:
                rule_triggered = True
                reason = f"rule: {metric} {value} > critical_high {critical_high}"
            if critical_low is not None and value < critical_low:
                rule_triggered = True
                reason = f"rule: {metric} {value} < critical_low {critical_low}"

            if rule_triggered:
                flagged = True
                severity = "high"  # rule-based criticals are always high

        if flagged:
            anomalies.append({
                "metric":   metric,
                "value":    value,
                "z_score":  z_score,
                "severity": severity,
                "reason":   reason,
            })

    return anomalies


# ---------------------------------------------------------------------------
# Shared fake baseline history (healthy person)
# ---------------------------------------------------------------------------

NORMAL_HISTORY = [
    {"heart_rate": 68, "sleep": 7.2, "steps": 8200, "stress_level": 3, "bmi": 22.1, "diet_score": 7.5},
    {"heart_rate": 72, "sleep": 6.8, "steps": 7800, "stress_level": 4, "bmi": 22.3, "diet_score": 7.0},
    {"heart_rate": 70, "sleep": 7.5, "steps": 9000, "stress_level": 3, "bmi": 22.0, "diet_score": 8.0},
    {"heart_rate": 69, "sleep": 7.0, "steps": 8500, "stress_level": 2, "bmi": 22.2, "diet_score": 7.8},
    {"heart_rate": 71, "sleep": 7.3, "steps": 8100, "stress_level": 3, "bmi": 22.1, "diet_score": 7.6},
    {"heart_rate": 68, "sleep": 6.9, "steps": 7900, "stress_level": 4, "bmi": 22.4, "diet_score": 7.2},
    {"heart_rate": 73, "sleep": 7.1, "steps": 8300, "stress_level": 3, "bmi": 22.0, "diet_score": 7.9},
]


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------

def _row(cols, widths):
    return "| " + " | ".join(str(c).ljust(w) for c, w in zip(cols, widths)) + " |"


def print_result_table(test_name: str, anomalies: list[dict]):
    headers = ["Metric", "Value", "Z-score", "Severity", "Reason"]
    widths   = [14, 8, 9, 10, 48]
    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"

    print(f"\n  {test_name}")
    if not anomalies:
        print("  (no anomalies detected)")
        return

    print("  " + sep)
    print("  " + _row(headers, widths))
    print("  " + sep)
    for a in anomalies:
        z = f"{a['z_score']:.2f}" if a["z_score"] is not None else "n/a"
        print("  " + _row(
            [a["metric"], a["value"], z, a["severity"], a["reason"]],
            widths,
        ))
    print("  " + sep)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_normal_reading():
    """All metrics within normal range — expect zero anomalies."""
    reading = {
        "heart_rate":  70,
        "sleep":        7.1,
        "steps":        8400,
        "stress_level": 3,
        "bmi":          22.2,
        "diet_score":   7.7,
    }
    baseline  = compute_baseline(NORMAL_HISTORY)
    anomalies = detect_anomalies(reading, baseline)
    print_result_table("TC-1: Normal reading", anomalies)

    assert len(anomalies) == 0, (
        f"Expected 0 anomalies for a normal reading, got {len(anomalies)}: {anomalies}"
    )
    return True


def test_heart_rate_spike():
    """Heart rate of 150 bpm vs baseline ~70 bpm — expect HIGH severity."""
    reading = {
        "heart_rate":  150,   # way above normal AND hits rule-based critical_high boundary
        "sleep":        7.0,
        "steps":        8200,
        "stress_level": 3,
        "bmi":          22.1,
        "diet_score":   7.5,
    }
    baseline  = compute_baseline(NORMAL_HISTORY)
    anomalies = detect_anomalies(reading, baseline)
    print_result_table("TC-2: Heart rate spike (150 bpm)", anomalies)

    hr_anomalies = [a for a in anomalies if a["metric"] == "heart_rate"]
    assert len(hr_anomalies) >= 1, "Expected at least one heart_rate anomaly"
    assert hr_anomalies[0]["severity"] == "high", (
        f"Expected 'high' severity for heart_rate spike, got '{hr_anomalies[0]['severity']}'"
    )
    return True


def test_sleep_crash():
    """Sleep of 2 h vs baseline ~7 h — expect medium or high severity anomaly."""
    reading = {
        "heart_rate":  71,
        "sleep":        2.0,   # far below normal
        "steps":        8000,
        "stress_level": 4,
        "bmi":          22.2,
        "diet_score":   7.6,
    }
    baseline  = compute_baseline(NORMAL_HISTORY)
    anomalies = detect_anomalies(reading, baseline)
    print_result_table("TC-3: Sleep crash (2 h)", anomalies)

    sleep_anomalies = [a for a in anomalies if a["metric"] == "sleep"]
    assert len(sleep_anomalies) >= 1, "Expected at least one sleep anomaly"
    assert sleep_anomalies[0]["severity"] in ("medium", "high"), (
        f"Expected 'medium' or 'high' severity for sleep crash, got '{sleep_anomalies[0]['severity']}'"
    )
    return True


def test_slightly_elevated_metric():
    """
    One metric (stress_level = 5) is slightly elevated but still within ~1σ
    of baseline mean ~3.  All other metrics are normal.
    Expect low or no anomaly for stress_level; zero anomalies overall.
    """
    reading = {
        "heart_rate":  70,
        "sleep":        7.0,
        "steps":        8300,
        "stress_level": 5,    # slightly elevated but not anomalous
        "bmi":          22.2,
        "diet_score":   7.6,
    }
    baseline  = compute_baseline(NORMAL_HISTORY)
    anomalies = detect_anomalies(reading, baseline)
    print_result_table("TC-4: Slightly elevated stress (stress=5)", anomalies)

    stress_anomalies = [a for a in anomalies if a["metric"] == "stress_level"]
    # If flagged, it must be 'low'; if not flagged at all, that's also acceptable.
    for sa in stress_anomalies:
        assert sa["severity"] == "low", (
            f"Expected 'low' severity for slight stress elevation, got '{sa['severity']}'"
        )
    # No other metrics should be anomalous
    other = [a for a in anomalies if a["metric"] != "stress_level"]
    assert len(other) == 0, f"Unexpected anomalies in other metrics: {other}"
    return True


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all():
    print("=" * 72)
    print("  DarpanAI — Anomaly Detection Unit Tests")
    print("=" * 72)

    tests = [
        ("TC-1: Normal reading",                test_normal_reading),
        ("TC-2: Heart rate spike (150 bpm)",    test_heart_rate_spike),
        ("TC-3: Sleep crash (2 h)",             test_sleep_crash),
        ("TC-4: Slightly elevated metric",      test_slightly_elevated_metric),
    ]

    passed = 0
    failed = 0
    failures = []

    for name, fn in tests:
        try:
            fn()
            passed += 1
        except AssertionError as exc:
            failed += 1
            failures.append((name, str(exc)))
            print(f"\n  FAIL — {name}\n  {exc}")

    print("\n" + "=" * 72)
    print(f"  Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 72)

    if failures:
        for name, msg in failures:
            print(f"  [FAIL] {name}: {msg}")
        sys.exit(1)
    else:
        print("All anomaly tests passed \u2713")


if __name__ == "__main__":
    run_all()
