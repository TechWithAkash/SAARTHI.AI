"""
Meta-Learner Ensemble Trainer (12-Feature ICMR)
Stacking Transformer and XGBoost models.
"""

import sys
import numpy as np
import pandas as pd
import joblib
import torch
from pathlib import Path
from tqdm import tqdm
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

sys.path.insert(0, str(Path(__file__).parent))
from train_l40s_sequence import DarpanTransformer

FEATURE_COLS = [
    "age", "gender", "bmi", "whr",
    "fam_diabetes", "fam_cvd", "fam_hypertension",
    "sleep_hours", "steps", "sugar_intake_g",
    "stress_level", "hrv_rmssd"
]
TARGET_COLS  = ['target_diabetes', 'target_cvd', 'target_hypertension']
SEED = 42

def extract_xgb_features(df):
    meta = joblib.load(Path(__file__).parent / "darpan_xgb_meta_icmr.pkl")
    static_cols = meta['static_cols']
    dyn_cols = meta['dynamic_cols']
    
    grouped = df.groupby('user_id')
    X_rows, y_rows = [], []
    for _, grp in grouped:
        grp = grp.sort_values('day')
        static = grp[static_cols].iloc[0].values
        dyn = grp[dyn_cols].values
        feat = list(static)
        for col_idx in range(5):
            col = dyn[:, col_idx]
            feat.extend([col.mean(), col.std(), col.min(), col.max()])
            feat.append(col[-7:].mean() - col[:7].mean())
            
        feat.append(float((dyn[:, 2] > 70).sum()))
        feat.append(float((dyn[:, 1] < 4000).sum()))
        feat.append(float((dyn[:, 3] > 7).sum()))
        feat.append(float((dyn[:, 0] < 5.5).sum()))
        X_rows.append(feat)
        y_rows.append(grp[TARGET_COLS].iloc[0].values)
    return np.array(X_rows, dtype=np.float32), np.array(y_rows, dtype=np.float32)

def build_sequence_tensor(df):
    grouped = list(df.groupby('user_id'))
    X_all, y_all = [], []
    for _, grp in grouped:
        grp = grp.sort_values('day')
        X_all.append(grp[FEATURE_COLS].values.astype(np.float32))
        y_all.append(grp[TARGET_COLS].iloc[0].values.astype(np.float32))
    return torch.from_numpy(np.array(X_all)), np.array(y_all, dtype=np.float32)

def train():
    data_dir = Path(__file__).parent
    df = pd.read_csv(data_dir / "timeseries_health_data_icmr.csv")

    user_ids = df['user_id'].unique()
    _, val_users = train_test_split(user_ids, test_size=0.15, random_state=SEED)
    val_df = df[df['user_id'].isin(val_users)].copy()
    
    X_seq, y_val = build_sequence_tensor(val_df)
    X_xgb, _     = extract_xgb_features(val_df)

    # 1. Transformer Preds
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = DarpanTransformer(
        norm_mean=df[FEATURE_COLS].mean().values,
        norm_std=df[FEATURE_COLS].std().values
    ).to(device)
    model.load_state_dict(torch.load(data_dir / "darpan_sequence_model_icmr.pth", map_location=device))
    model.eval()

    transformer_preds = []
    with torch.no_grad():
        for start in range(0, len(X_seq), 1024):
            batch = X_seq[start:start+1024].to(device)
            transformer_preds.append(model(batch).cpu().numpy())
    transformer_preds = np.vstack(transformer_preds)

    # 2. XGBoost Preds
    xgb_preds = np.zeros((len(X_xgb), 3), dtype=np.float32)
    for i, disease in enumerate(['diabetes', 'cvd', 'hypertension']):
        m = joblib.load(data_dir / f"darpan_xgb_{disease}_icmr.pkl")
        xgb_preds[:, i] = m.predict(X_xgb)

    # 3. Meta-learner
    meta_X = np.hstack([transformer_preds, xgb_preds])
    final_meta = Ridge(alpha=0.1, fit_intercept=True)
    final_meta.fit(meta_X, y_val)
    ensemble_preds = final_meta.predict(meta_X)

    print("\n" + "="*50)
    print("  12-FEATURE ENSEMBLE FINAL RESULTS")
    print("  ---------------------------------")
    for i, d in enumerate(['Diabetes', 'CVD', 'Hypertension']):
        r2 = r2_score(y_val[:, i], ensemble_preds[:, i])
        mae = mean_absolute_error(y_val[:, i], ensemble_preds[:, i])
        print(f"  {d:<15} R²={r2:.4f}  MAE={mae:.2f}%")
    print("="*50 + "\n")

    joblib.dump({
        'meta_learner': final_meta,
        'model_order':  ['transformer', 'xgboost']
    }, data_dir / "darpan_meta_weights_icmr.pkl")

if __name__ == "__main__":
    train()
