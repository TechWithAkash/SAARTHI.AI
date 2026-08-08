"""
XGBoost Health Risk Models — Ensemble Component 2 (12-Feature ICMR)
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from tqdm import tqdm
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

STATIC_COLS  = ['age', 'gender', 'bmi', 'whr', 'fam_diabetes', 'fam_cvd', 'fam_hypertension']
DYNAMIC_COLS = ['sleep_hours', 'steps', 'sugar_intake_g', 'stress_level', 'hrv_rmssd']
TARGET_COLS  = ['target_diabetes', 'target_cvd', 'target_hypertension']

SUGAR_THRESH = 70  # ICMR threshold was changed to 70 in new generator
STEPS_THRESH = 4000 # changed to 4000
STRESS_THRESH = 7
SLEEP_THRESH  = 5.5 # changed to 5.5

SEED = 42

def extract_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    grouped = df.groupby('user_id')
    X_rows, y_rows = [], []

    for _, grp in tqdm(grouped, desc="Feature engineering", ncols=80):
        grp = grp.sort_values('day')

        static = grp[STATIC_COLS].iloc[0].values
        dyn = grp[DYNAMIC_COLS].values   # shape (30, 5)

        feat = list(static)
        for col_idx in range(5):
            col = dyn[:, col_idx]
            feat.extend([col.mean(), col.std(), col.min(), col.max()])
            feat.append(col[-7:].mean() - col[:7].mean())

        # Bad-day counts based on the updated logic in generator
        feat.append(float((dyn[:, 2] > SUGAR_THRESH).sum()))   
        feat.append(float((dyn[:, 1] < STEPS_THRESH).sum()))   
        feat.append(float((dyn[:, 3] > STRESS_THRESH).sum()))  
        feat.append(float((dyn[:, 0] < SLEEP_THRESH).sum()))   

        targets = grp[TARGET_COLS].iloc[0].values
        X_rows.append(feat)
        y_rows.append(targets)

    return np.array(X_rows, dtype=np.float32), np.array(y_rows, dtype=np.float32)

def train_xgb_model(X_train, y_train, X_val, y_val, target_name: str):
    model = xgb.XGBRegressor(
        n_estimators=1000, learning_rate=0.05, max_depth=6,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
        reg_alpha=0.1, reg_lambda=1.0, objective='reg:squarederror',
        tree_method='hist', device='cuda', eval_metric='rmse',
        random_state=SEED, n_jobs=-1,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=100)
    
    val_preds = model.predict(X_val)
    r2  = r2_score(y_val, val_preds)
    mae = mean_absolute_error(y_val, val_preds)
    print(f"  [{target_name}]  Val R²={r2:.4f}  Val MAE={mae:.2f}%")
    return model

def train():
    data_path = Path(__file__).parent / "timeseries_health_data_icmr.csv"
    out_dir   = Path(__file__).parent

    if not data_path.exists():
        print("Run generate_timeseries_data.py first.")
        return

    df = pd.read_csv(data_path)
    X, y = extract_features(df)

    print(f"XGB Feature matrix: {X.shape}  |  Targets: {y.shape}")
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.15, random_state=SEED)

    models = {}
    for i, disease in enumerate(['diabetes', 'cvd', 'hypertension']):
        print(f"\nTraining XGBoost → {disease.upper()} ...")
        model = train_xgb_model(X_train, y_train[:, i], X_val, y_val[:, i], target_name=disease)
        models[disease] = model
        joblib.dump(model, out_dir / f"darpan_xgb_{disease}_icmr.pkl")

    meta = {'static_cols': STATIC_COLS, 'dynamic_cols': DYNAMIC_COLS, 'n_features': X.shape[1]}
    joblib.dump(meta, out_dir / "darpan_xgb_meta_icmr.pkl")
    print(f"========================================================\n")

if __name__ == "__main__":
    train()
