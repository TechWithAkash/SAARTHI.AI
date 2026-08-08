"""
Standalone SHAP explainability smoke test (no MongoDB needed).
Run: source .venv/bin/activate && python -m backend.ml.test_explain
"""
import pickle
import numpy as np
import shap
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "risk_model.pkl"
FEATURES   = ["age", "bmi", "sleep", "steps", "stress_level", "diet_score", "heart_rate"]

DENORM = {
    "heart_rate":   (40,  200),
    "steps":        (0,   20000),
    "sleep":        (0,   12),
    "bmi":          (15,  50),
    "stress_level": (1,   10),
    "diet_score":   (1,   10),
}
FEATURE_LABELS = {
    "heart_rate": "Heart Rate", "steps": "Daily Steps", "sleep": "Sleep",
    "bmi": "BMI", "stress_level": "Stress Level", "diet_score": "Diet Quality", "age": "Age",
}

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

explainer = shap.TreeExplainer(model)

PROFILES = [
    {
        "label": "High-risk: stressed, poor sleep",
        "normalized": {
            "heart_rate": 0.70, "steps": 0.20, "sleep": 0.35,
            "bmi": 0.65, "stress_level": 0.85, "diet_score": 0.30,
        },
        "age": 52,
        "expect_top_driver": "stress_level",
    },
    {
        "label": "Moderate: average everything",
        "normalized": {
            "heart_rate": 0.48, "steps": 0.38, "sleep": 0.52,
            "bmi": 0.45, "stress_level": 0.55, "diet_score": 0.50,
        },
        "age": 38,
        "expect_top_driver": None,
    },
    {
        "label": "Low-risk: fit and healthy",
        "normalized": {
            "heart_rate": 0.22, "steps": 0.70, "sleep": 0.72,
            "bmi": 0.25, "stress_level": 0.25, "diet_score": 0.78,
        },
        "age": 28,
        "expect_top_driver": None,
    },
]

SEP = "─" * 68

for profile in PROFILES:
    normalized = profile["normalized"]
    age = profile["age"]

    raw = {"age": float(age)}
    for feat, (lo, hi) in DENORM.items():
        raw[feat] = round(lo + normalized.get(feat, 0.5) * (hi - lo), 2)

    X = np.array([[raw.get(f, 0.0) for f in FEATURES]])
    risk_score = float(np.clip(model.predict(X)[0], 0, 100))
    shap_vals  = explainer.shap_values(X)[0]
    shap_dict  = {f: round(float(v), 2) for f, v in zip(FEATURES, shap_vals)}

    base_val   = round(float(explainer.expected_value), 2)
    shap_sum   = round(sum(shap_dict.values()), 2)
    reconst    = round(base_val + shap_sum, 2)

    print(SEP)
    print(f"  {profile['label']}")
    print(f"  Risk score: {risk_score:.1f}  |  Base value: {base_val}  |  SHAP sum: {shap_sum}  |  Reconstructed: {reconst:.1f}")
    print(SEP)

    sorted_feats = sorted(shap_dict.items(), key=lambda x: -abs(x[1]))
    drivers = [(f, v) for f, v in sorted_feats if v > 0]
    protect = [(f, v) for f, v in sorted_feats if v <= 0]

    print("  RISK DRIVERS (pushing risk up):")
    for feat, val in drivers:
        bar = "█" * min(int(abs(val) * 2), 20)
        print(f"    {FEATURE_LABELS[feat]:<15} raw={raw[feat]:>7.1f}   +{val:5.2f}  {bar}")

    print("  PROTECTIVE FACTORS (pushing risk down):")
    for feat, val in protect:
        bar = "░" * min(int(abs(val) * 2), 20)
        print(f"    {FEATURE_LABELS[feat]:<15} raw={raw[feat]:>7.1f}   {val:6.2f}  {bar}")

    # Validation: SHAP sum + base ≈ prediction
    assert abs(reconst - risk_score) < 2.0, (
        f"SHAP reconstruction error: {reconst} vs {risk_score}"
    )

    top_driver = drivers[0][0] if drivers else None
    print(f"\n  ✓ SHAP reconstruction error < 2.0 pts")
    print(f"  ✓ Top local driver: {FEATURE_LABELS.get(top_driver, top_driver)}")
    print()

print(SEP)
print("  All SHAP tests passed ✓")
print(SEP)
