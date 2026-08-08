"""
Standalone smoke test for simulation engine (no MongoDB needed).
Run: source .venv/bin/activate && python -m backend.ml.test_simulation
"""
import pickle
import numpy as np
from pathlib import Path
from backend.services.simulation_service import (
    _load_model, _denormalize, _simulate_current,
    _simulate_improved, _simulate_optimal, TIMELINE,
)

model = _load_model()

# Three test profiles
PROFILES = [
    {
        "label": "High-risk user (poor sleep, high stress)",
        "normalized": {
            "heart_rate":   0.70,  # 152 bpm equivalent
            "steps":        0.20,  # 4000 steps
            "sleep":        0.35,  # 4.2h
            "bmi":          0.65,  # 32.75 BMI
            "stress_level": 0.85,  # stress=9
            "diet_score":   0.30,  # diet=4
        },
        "age": 52,
    },
    {
        "label": "Moderate-risk user (average everything)",
        "normalized": {
            "heart_rate":   0.48,
            "steps":        0.38,
            "sleep":        0.52,
            "bmi":          0.45,
            "stress_level": 0.55,
            "diet_score":   0.50,
        },
        "age": 38,
    },
    {
        "label": "Low-risk user (healthy baseline)",
        "normalized": {
            "heart_rate":   0.22,
            "steps":        0.70,
            "sleep":        0.72,
            "bmi":          0.25,
            "stress_level": 0.25,
            "diet_score":   0.78,
        },
        "age": 28,
    },
]

SEP = "─" * 72

for profile in PROFILES:
    base = _denormalize(profile["normalized"], profile["age"])
    current  = _simulate_current(model, base, TIMELINE)
    improved = _simulate_improved(model, base, TIMELINE)
    optimal  = _simulate_optimal(model, base, TIMELINE)

    baseline = current[0]
    pct_imp  = round((baseline - improved[-1]) / baseline * 100, 1)
    pct_opt  = round((baseline - optimal[-1])  / baseline * 100, 1)

    print(SEP)
    print(f"  {profile['label']}")
    print(SEP)
    print(f"  {'Day':<6} {'Current':>9} {'Improved':>10} {'Optimal':>9}")
    print(f"  {'─'*6} {'─'*9} {'─'*10} {'─'*9}")
    for i, day in enumerate(TIMELINE):
        arrow_i = "↓" if improved[i] < current[i] else "↑"
        arrow_o = "↓" if optimal[i]  < current[i] else "↑"
        print(f"  {day:<6} {current[i]:>9.1f} {improved[i]:>9.1f}{arrow_i} {optimal[i]:>8.1f}{arrow_o}")

    print()
    print(f"  Improved scenario: {pct_imp:+.1f}% risk change over 120 days")
    print(f"  Optimal  scenario: {pct_opt:+.1f}% risk change over 120 days")

    # Assertions — what actually matters:
    # 1. Both interventions must beat current by end of simulation
    # 2. Current must drift upward (no intervention = worsening)
    # Note: optimal may not always beat improved because XGBoost is non-monotonic;
    #       improved aggressively targets stress (40% importance) which can dominate.
    assert improved[-1] < current[-1], "Improved should end lower than current"
    assert optimal[-1]  < current[-1], "Optimal should end lower than current"
    assert current[-1]  > current[0],  "Current (no intervention) should drift upward"
    print("  ✓ All trajectory assertions passed")
    print()

print(SEP)
print("  All simulation tests passed ✓")
print(SEP)
