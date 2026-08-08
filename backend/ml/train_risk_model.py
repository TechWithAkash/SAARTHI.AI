"""
XGBoost risk model trainer.
Run: python -m backend.ml.train_risk_model
Outputs: backend/ml/risk_model.pkl  +  backend/ml/risk_model_meta.json
"""
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import MinMaxScaler

from backend.ml.generate_dataset import generate

FEATURES = ["age", "bmi", "sleep", "steps", "stress_level", "diet_score", "heart_rate"]
TARGET = "risk_score"
MODEL_DIR = Path(__file__).parent


def train():
    # ── 1. Data ──────────────────────────────────────────────────────────────
    csv = MODEL_DIR / "health_dataset.csv"
    df = pd.read_csv(csv) if csv.exists() else generate()

    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # ── 2. Model ──────────────────────────────────────────────────────────────
    model = XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # ── 3. Evaluate ───────────────────────────────────────────────────────────
    preds = model.predict(X_test)
    mae   = mean_absolute_error(y_test, preds)
    r2    = r2_score(y_test, preds)
    cv    = cross_val_score(model, X, y, cv=5, scoring="r2")

    print(f"MAE:        {mae:.2f} risk points")
    print(f"R²:         {r2:.4f}")
    print(f"CV R² (5f): {cv.mean():.4f} ± {cv.std():.4f}")

    imp = dict(zip(FEATURES, model.feature_importances_.round(4).tolist()))
    print("\nFeature importances:")
    for k, v in sorted(imp.items(), key=lambda x: -x[1]):
        print(f"  {k:<15} {v:.4f}")

    # ── 4. Save ───────────────────────────────────────────────────────────────
    model_path = MODEL_DIR / "risk_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    meta = {
        "version":             "xgb_v1.0",
        "features":            FEATURES,
        "mae":                 round(mae, 2),
        "r2":                  round(r2, 4),
        "cv_r2_mean":          round(float(cv.mean()), 4),
        "feature_importances": imp,
        "n_train":             len(X_train),
        "n_test":              len(X_test),
    }
    meta_path = MODEL_DIR / "risk_model_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    print(f"\nModel saved → {model_path}")
    print(f"Meta  saved → {meta_path}")
    return model, meta


if __name__ == "__main__":
    train()
