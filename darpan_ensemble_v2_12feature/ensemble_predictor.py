"""
DarpanEnsemble — Production Predictor (12-Feature ICMR)
"""

import sys
import numpy as np
import torch
import joblib
from pathlib import Path
from typing import Union

_DIR = Path(__file__).parent
sys.path.insert(0, str(_DIR))

from train_l40s_sequence import DarpanTransformer

FEATURE_COLS = [
    "age", "gender", "bmi", "whr",
    "fam_diabetes", "fam_cvd", "fam_hypertension",
    "sleep_hours", "steps", "sugar_intake_g",
    "stress_level", "hrv_rmssd"
]

def _extract_xgb_features(x: np.ndarray) -> np.ndarray:
    B = x.shape[0]
    rows = []
    for i in range(B):
        days   = x[i]
        static = days[0, :7] 
        dyn    = days[:, 7:] 
        feat   = list(static)
        for col_idx in range(5):
            col = dyn[:, col_idx]
            feat.extend([col.mean(), col.std(), col.min(), col.max()])
            feat.append(col[-7:].mean() - col[:7].mean())
        feat.append(float((dyn[:, 2] > 70).sum()))
        feat.append(float((dyn[:, 1] < 4000).sum()))
        feat.append(float((dyn[:, 3] > 7).sum()))
        feat.append(float((dyn[:, 0] < 5.5).sum()))
        rows.append(feat)
    return np.array(rows, dtype=np.float32)

class DarpanEnsemble:
    def __init__(self, transformer, xgb_diabetes, xgb_cvd, xgb_hypertension, meta_learner, device):
        self.transformer = transformer
        self.xgb_diabetes = xgb_diabetes
        self.xgb_cvd = xgb_cvd
        self.xgb_hypertension = xgb_hypertension
        self.meta_learner = meta_learner
        self.device = device

    @classmethod
    def load(cls, model_dir: Union[str, Path], device_str: str = "auto"):
        model_dir = Path(model_dir)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu") if device_str == "auto" else torch.device(device_str)

        # Retrieve normalization stats from the original dataset if needed, 
        # but DarpanTransformer needs dummy ones to gen class, then load_state_dict overwrites them
        transformer = DarpanTransformer(
            norm_mean=np.zeros(12, dtype=np.float32),
            norm_std=np.ones(12, dtype=np.float32)
        ).to(device)
        transformer.load_state_dict(torch.load(model_dir / "darpan_sequence_model_icmr.pth", map_location=device))
        transformer.eval()

        xgb_diabetes     = joblib.load(model_dir / "darpan_xgb_diabetes_icmr.pkl")
        xgb_cvd          = joblib.load(model_dir / "darpan_xgb_cvd_icmr.pkl")
        xgb_hypertension = joblib.load(model_dir / "darpan_xgb_hypertension_icmr.pkl")

        meta_bundle  = joblib.load(model_dir / "darpan_meta_weights_icmr.pkl")
        
        return cls(transformer, xgb_diabetes, xgb_cvd, xgb_hypertension, meta_bundle['meta_learner'], device)

    def predict(self, x: np.ndarray) -> np.ndarray:
        x_tensor = torch.from_numpy(x).to(self.device)
        with torch.no_grad():
            t_preds = self.transformer(x_tensor).cpu().numpy()

        x_xgb = _extract_xgb_features(x)
        xgb_preds = np.column_stack([
            self.xgb_diabetes.predict(x_xgb),
            self.xgb_cvd.predict(x_xgb),
            self.xgb_hypertension.predict(x_xgb),
        ])

        meta_input  = np.hstack([t_preds, xgb_preds])
        ensemble_out = self.meta_learner.predict(meta_input)

        return np.clip(ensemble_out, 0.0, 100.0).astype(np.float32)

    def predict_single(self, thirty_day_sequence: list) -> dict:
        x = np.array([[
            [day[k] for k in FEATURE_COLS] for day in thirty_day_sequence
        ]], dtype=np.float32)
        out = self.predict(x)
        
        return {
            "diabetes_risk":     round(float(out[0, 0]), 2),
            "cvd_risk":          round(float(out[0, 1]), 2),
            "hypertension_risk": round(float(out[0, 2]), 2),
        }

if __name__ == "__main__":
    ensemble = DarpanEnsemble.load(_DIR)
    
    # 37yr Female, Borderline overweight (12-features)
    patient = [{
        'age': 37, 'gender': 1, 'bmi': 24.0, 'whr': 0.85,
        'fam_diabetes': 1, 'fam_cvd': 0, 'fam_hypertension': 0,
        'sleep_hours': 6.5, 'steps': 6000, 'sugar_intake_g': 60,
        'stress_level': 5, 'hrv_rmssd': 35.0
    }] * 30

    print("\n[DarpanEnsemble 12-Feature] Testing:")
    res = ensemble.predict_single(patient)
    for k, v in res.items():
        print(f"  {k}: {v}%")
    print("\n✓ Ensemble Ready.")
