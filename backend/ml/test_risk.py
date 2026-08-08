"""
Smoke test for risk model predictions.
Run: source .venv/bin/activate && python -m backend.ml.test_risk
"""
import pickle
import json
import numpy as np
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "risk_model.pkl"
META_PATH  = Path(__file__).parent / "risk_model_meta.json"
FEATURES   = ["age", "bmi", "sleep", "steps", "stress_level", "diet_score", "heart_rate"]

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)
meta = json.loads(META_PATH.read_text())

test_cases = [
    {
        "label":  "Healthy young adult",
        "values": dict(age=25, bmi=22, sleep=8, steps=10000, stress_level=3, diet_score=8, heart_rate=62),
        "expect": "Low",
    },
    {
        "label":  "Moderate risk middle-aged",
        "values": dict(age=45, bmi=27, sleep=6.5, steps=5000, stress_level=6, diet_score=5, heart_rate=74),
        "expect": "Moderate",
    },
    {
        "label":  "High risk sedentary",
        "values": dict(age=60, bmi=33, sleep=5, steps=2000, stress_level=8, diet_score=3, heart_rate=92),
        "expect": "High",
    },
    {
        "label":  "Critical — elderly, obese, stressed",
        "values": dict(age=72, bmi=40, sleep=4, steps=800, stress_level=10, diet_score=2, heart_rate=110),
        "expect": "Critical",
    },
]

THRESHOLDS = [(0,30,"Low"),(30,52,"Moderate"),(52,68,"High"),(68,101,"Critical")]

def categorize(s):
    for lo, hi, label in THRESHOLDS:
        if lo <= s < hi: return label
    return "Critical"

print(f"Model v{meta['version']} | MAE={meta['mae']} | R²={meta['r2']}\n")
print(f"{'Case':<35} {'Score':>6}  {'Category':<10}  {'Expected':<10}  {'OK'}")
print("─" * 75)
all_ok = True
for tc in test_cases:
    X = np.array([[tc["values"][f] for f in FEATURES]])
    score = float(np.clip(model.predict(X)[0], 0, 100))
    cat   = categorize(score)
    ok    = "✓" if cat == tc["expect"] else "✗"
    if cat != tc["expect"]: all_ok = False
    print(f"{tc['label']:<35} {score:>6.1f}  {cat:<10}  {tc['expect']:<10}  {ok}")

print("\n" + ("All tests passed ✓" if all_ok else "Some tests failed ✗"))
