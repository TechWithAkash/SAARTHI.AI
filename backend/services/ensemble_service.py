"""
DarpanAI — Ensemble Inference Service (12-Feature ICMR Edition)
================================================================
Loads the Transformer + 3x XGBoost + meta-learner ensemble once at startup,
then exposes a fast synchronous predict() for use by risk_service.

Works on:
  - Apple M4 (CPU — fast enough for a 10MB model)
  - Any CUDA GPU
  - CPU-only (fallback)

Usage:
    from backend.services.ensemble_service import get_ensemble, predict_risk

    result = predict_risk(user_health_dict)
    # → {"diabetes_risk": 23.4, "cvd_risk": 11.2, "hypertension_risk": 18.7,
    #    "composite_risk": 19.5, "risk_category": "Low", "top_risk_factors": [...]}

IMPORTANT — macOS ARM OpenMP fix
---------------------------------
PyTorch 2.x bundles its own OpenMP (libomp). XGBoost 3.x on macOS also uses
Apple Accelerate / libomp. When both are imported in the same Python process,
a race condition in the OpenMP thread pool causes a SIGSEGV (segfault).
Setting OMP_NUM_THREADS=1 BEFORE any import serializes the thread pools
and prevents the crash. This must be the FIRST thing in this module.
"""

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import logging
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any

import numpy as np
import torch
import joblib

# Suppress noisy xgboost device warning on Mac (XGBoost was trained on CUDA,
# runs fine on CPU — it just warns about device mismatch)
warnings.filterwarnings("ignore", category=UserWarning, module="xgboost")

from backend.ml.darpan_transformer import DarpanTransformer

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent / "ml"

# 12 ICMR feature columns (order must match training)
FEATURE_COLS = [
    "age", "gender", "bmi", "whr",
    "fam_diabetes", "fam_cvd", "fam_hypertension",
    "sleep_hours", "steps", "sugar_intake_g",
    "stress_level", "hrv_rmssd",
]

STATIC_DIM  = 7   # first 7 are static
DYNAMIC_DIM = 5   # last 5 vary day-to-day

SEQUENCE_LEN = 30

CATEGORY_THRESHOLDS = [
    (0,  20,  "Low"),
    (20, 40,  "Moderate"),
    (40, 60,  "High"),
    (60, 101, "Critical"),
]

# ── Calibration + composite weights (single source of truth) ──────────────────
# Post-hoc calibration: dampen diabetes and CVD to realistic clinical ranges.
# The ensemble was trained on high-risk ICMR cohorts and over-predicts for
# population-level use. Hypertension is already in a realistic band.
# HARDCODED[HC-01]: 0.73 is an undefended constant — pending NHANES calibration.
DISEASE_SCALE = {
    "diabetes_risk":     0.73,
    "cvd_risk":          0.73,
    "hypertension_risk": 1.00,
}

# HARDCODED[HC-02]: composite weights are a product judgement, not derived.
COMPOSITE_WEIGHTS = {
    "diabetes_risk":     0.35,
    "cvd_risk":          0.40,
    "hypertension_risk": 0.25,
}

DISEASES = ["diabetes_risk", "cvd_risk", "hypertension_risk"]

# ── XGBoost engineered-feature schema ─────────────────────────────────────────
# _extract_xgb_features() builds a 36-dim vector in this exact order:
#   [0:7]   the 7 static ICMR features, taken from day 0
#   [7:32]  per dynamic feature (5 of them) x 5 stats: mean, std, min, max, trend
#   [32:36] 4 clinical threshold counts
# Both lists below MUST stay in lockstep with _extract_xgb_features().

_DYN_COLS  = FEATURE_COLS[STATIC_DIM:]          # sleep_hours, steps, sugar_intake_g, stress_level, hrv_rmssd
_DYN_STATS = ["mean", "std", "min", "max", "trend_7d"]

_THRESHOLD_FEATURES = [
    ("high_sugar_days",  "sugar_intake_g"),     # dyn[:, 2] > 70
    ("low_steps_days",   "steps"),              # dyn[:, 1] < 4000
    ("high_stress_days", "stress_level"),       # dyn[:, 3] > 7
    ("poor_sleep_days",  "sleep_hours"),        # dyn[:, 0] < 5.5
]

XGB_FEATURE_NAMES: list[str] = (
    list(FEATURE_COLS[:STATIC_DIM])
    + [f"{col}_{stat}" for col in _DYN_COLS for stat in _DYN_STATS]
    + [name for name, _ in _THRESHOLD_FEATURES]
)

# Maps each of the 36 engineered features back to the base ICMR feature it
# derives from, so SHAP attributions can be grouped into 12 interpretable rows.
XGB_BASE_OF: list[str] = (
    list(FEATURE_COLS[:STATIC_DIM])
    + [col for col in _DYN_COLS for _ in _DYN_STATS]
    + [base for _, base in _THRESHOLD_FEATURES]
)

assert len(XGB_FEATURE_NAMES) == len(XGB_BASE_OF) == 36, "XGB feature schema drift"

# The 12 ICMR features are derived from DarpanAI's 6 tracked vitals. This maps
# each back so the existing /insights contract keeps working.
ICMR_TO_LEGACY = {
    "sleep_hours":    "sleep",
    "steps":          "steps",
    "stress_level":   "stress_level",
    "bmi":            "bmi",
    "sugar_intake_g": "diet_score",   # sugar is derived from diet_score
    "hrv_rmssd":      "heart_rate",   # HRV is derived from (or measured alongside) HR
    "age":            "age",
}


def _best_device() -> torch.device:
    """
    Returns CPU for now.

    MPS (Apple Silicon) causes a segfault when loading CUDA-trained .pth files
    with weights_only=True on PyTorch 2.x. Since DarpanTransformer is only ~10MB,
    CPU inference on M4 is ~1ms — practically instant. Re-enable MPS once the
    model is re-serialized natively by running:
        torch.save(model.state_dict(), "...icmr.pth")
    after loading on CPU once.
    """
    # TODO: Switch back to MPS after re-serializing the .pth on Mac
    # if torch.backends.mps.is_available():
    #     return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _extract_xgb_features(x: np.ndarray) -> np.ndarray:
    """Extract hand-crafted statistical features for the XGBoost layer."""
    B    = x.shape[0]
    rows = []
    for i in range(B):
        days   = x[i]           # [30, 12]
        static = days[0, :7]    # take static from day-0 (same each day)
        dyn    = days[:, 7:]    # [30, 5] — dynamic features

        feat = list(static)
        for col_idx in range(5):
            col = dyn[:, col_idx]
            feat.extend([col.mean(), col.std(), col.min(), col.max()])
            feat.append(col[-7:].mean() - col[:7].mean())   # 7-day trend

        # Threshold counts (clinical signals)
        feat.append(float((dyn[:, 2] > 70).sum()))   # high sugar days
        feat.append(float((dyn[:, 1] < 4000).sum())) # low-steps days
        feat.append(float((dyn[:, 3] > 7).sum()))    # high stress days
        feat.append(float((dyn[:, 0] < 5.5).sum()))  # poor sleep days

        rows.append(feat)
    return np.array(rows, dtype=np.float32)


class DarpanEnsemble:
    """Loaded-once singleton that performs ensemble inference."""

    def __init__(self, transformer, xgb_diabetes, xgb_cvd, xgb_hypertension,
                 meta_learner, device):
        self.transformer      = transformer
        self.xgb_diabetes     = xgb_diabetes
        self.xgb_cvd          = xgb_cvd
        self.xgb_hypertension = xgb_hypertension
        self.meta_learner     = meta_learner
        self.device           = device

    @classmethod
    def load(cls) -> "DarpanEnsemble":
        device = _best_device()
        logger.info(f"[DarpanEnsemble] Loading models onto {device}")

        # Load the Transformer backbone
        transformer = DarpanTransformer(
            norm_mean=np.zeros(12, dtype=np.float32),
            norm_std=np.ones(12,  dtype=np.float32),
        ).to(device)
        transformer.load_state_dict(
            torch.load(
                MODEL_DIR / "darpan_sequence_model_icmr.pth",
                map_location=device,
                weights_only=True,
            )
        )
        transformer.eval()

        # XGBoost specialists (CPU-only, joblib)
        xgb_diabetes     = joblib.load(MODEL_DIR / "darpan_xgb_diabetes_icmr.pkl")
        xgb_cvd          = joblib.load(MODEL_DIR / "darpan_xgb_cvd_icmr.pkl")
        xgb_hypertension = joblib.load(MODEL_DIR / "darpan_xgb_hypertension_icmr.pkl")

        # Meta-learner (Ridge)
        meta_bundle   = joblib.load(MODEL_DIR / "darpan_meta_weights_icmr.pkl")
        meta_learner  = meta_bundle["meta_learner"]

        logger.info("[DarpanEnsemble] ✓ All models loaded successfully")
        return cls(transformer, xgb_diabetes, xgb_cvd, xgb_hypertension, meta_learner, device)

    def predict_batch(self, x: np.ndarray) -> np.ndarray:
        """
        x: float32 array [B, 30, 12]
        Returns: float32 array [B, 3] — (diabetes%, cvd%, hypertension%)
        """
        x_tensor = torch.from_numpy(x).to(self.device)

        with torch.no_grad():
            t_preds = self.transformer(x_tensor).cpu().numpy()  # [B, 3]

        x_xgb    = _extract_xgb_features(x)
        xgb_preds = np.column_stack([
            self.xgb_diabetes.predict(x_xgb),
            self.xgb_cvd.predict(x_xgb),
            self.xgb_hypertension.predict(x_xgb),
        ])                                                       # [B, 3]

        meta_input   = np.hstack([t_preds, xgb_preds])         # [B, 6]
        ensemble_out = self.meta_learner.predict(meta_input)    # [B, 3]

        return np.clip(ensemble_out, 0.0, 100.0).astype(np.float32)

    def predict_single(self, thirty_day_sequence: list) -> dict:
        """thirty_day_sequence: list of 30 dicts, each with the 12 ICMR keys."""
        x = self.to_array(thirty_day_sequence)
        out = self.predict_batch(x)
        return {
            "diabetes_risk":     round(float(out[0, 0]), 2),
            "cvd_risk":          round(float(out[0, 1]), 2),
            "hypertension_risk": round(float(out[0, 2]), 2),
        }

    def predict_single_checked(self, thirty_day_sequence: list) -> tuple[dict, bool]:
        """
        Like predict_single, but also reports whether the XGBoost heads
        saturated on this input (see decompose()'s XGB_SATURATION_MARGIN).
        Callers use this to decide whether the result is trustworthy enough
        to show, or whether to fall back to a safer input.
        """
        x = self.to_array(thirty_day_sequence)
        parts = self.decompose(x)
        out = parts["ensemble_out"]
        return {
            "diabetes_risk":     round(float(out[0, 0]), 2),
            "cvd_risk":          round(float(out[0, 1]), 2),
            "hypertension_risk": round(float(out[0, 2]), 2),
        }, parts["saturated"]

    @staticmethod
    def to_array(thirty_day_sequence: list) -> np.ndarray:
        """list[30 dicts] → float32 [1, 30, 12] in FEATURE_COLS order."""
        return np.array([[
            [day[k] for k in FEATURE_COLS] for day in thirty_day_sequence
        ]], dtype=np.float32)

    @property
    def xgb_heads(self) -> dict:
        """Disease → fitted XGBoost specialist, keyed to match DISEASES."""
        return {
            "diabetes_risk":     self.xgb_diabetes,
            "cvd_risk":          self.xgb_cvd,
            "hypertension_risk": self.xgb_hypertension,
        }

    def meta_xgb_weights(self) -> np.ndarray:
        """
        The Ridge meta-learner takes 6 inputs: [t_diab, t_cvd, t_hyper,
        xgb_diab, xgb_cvd, xgb_hyper] and emits 3 outputs. Returns the 3x3
        block of coefficients mapping the *XGBoost* predictions onto each
        output, i.e. how much of each final score the XGB heads account for.

        This is what makes SHAP-over-XGB an exact partial attribution rather
        than a hand-wave: output_d = sum_h W[d, h] * xgb_pred_h + (transformer
        terms) + intercept, so W[d, h] * shap_h is the true contribution of
        head h's features to output d.
        """
        return np.asarray(self.meta_learner.coef_, dtype=np.float64)[:, 3:6]

    def meta_transformer_weights(self) -> np.ndarray:
        """The 3x3 block mapping transformer predictions onto each output."""
        return np.asarray(self.meta_learner.coef_, dtype=np.float64)[:, 0:3]

    # A well-trained regressor for a 0-100 target overshoots by a few points at
    # most on in-distribution data. Anything beyond this margin means the
    # engineered features (std/min/max/trend over a real 30-day window) landed
    # far outside anything the XGBoost heads saw in training — a genuine
    # extrapolation failure, not a genuinely-near-zero-or-maximal risk finding.
    XGB_SATURATION_MARGIN = 15.0

    def decompose(self, x: np.ndarray) -> dict:
        """
        Runs the ensemble and returns the intermediate parts, so callers can
        attribute a final score to the transformer vs the XGBoost specialists
        instead of treating the meta-learner as a black box.
        """
        x_tensor = torch.from_numpy(x).to(self.device)
        with torch.no_grad():
            t_preds = self.transformer(x_tensor).cpu().numpy()

        x_xgb = _extract_xgb_features(x)
        xgb_preds = np.column_stack([
            self.xgb_diabetes.predict(x_xgb),
            self.xgb_cvd.predict(x_xgb),
            self.xgb_hypertension.predict(x_xgb),
        ])

        meta_input = np.hstack([t_preds, xgb_preds])
        raw_out = self.meta_learner.predict(meta_input)
        out = np.clip(raw_out, 0.0, 100.0)

        # Saturation check on the UNCLIPPED xgb_preds — clipping happens later
        # and would hide exactly the signal we need. xgb_preds this far outside
        # [0,100] means the input triggered leaf paths the trees never learned
        # sensible values for, not a real "very low/high risk" finding.
        margin = self.XGB_SATURATION_MARGIN
        saturated = bool(np.any((xgb_preds < -margin) | (xgb_preds > 100 + margin)))

        return {
            "xgb_input":         x_xgb,          # [B, 36]
            "transformer_preds": t_preds,        # [B, 3]
            "xgb_preds":         xgb_preds,      # [B, 3] — UNCLIPPED, the saturation signal
            "ensemble_out":      out,            # [B, 3] — clipped, what's actually displayed
            "raw_ensemble_out":  raw_out,         # [B, 3] — unclipped, for diagnostics
            "saturated":         saturated,
        }


# ── Module-level singleton ────────────────────────────────────────────────────

_ensemble: DarpanEnsemble | None = None


def get_ensemble() -> DarpanEnsemble:
    """Returns the singleton ensemble, loading it on first call."""
    global _ensemble
    if _ensemble is None:
        _ensemble = DarpanEnsemble.load()
    return _ensemble


def derive_hrv(heart_rate: float) -> float:
    """
    HRV proxy from resting HR when no measured RMSSD is available.

    HARDCODED[HC-03]: this is a monotone stand-in, NOT a clinical HRV estimate.
    Real RMSSD comes from a wearable (see garmin_service.fetch_enhancements);
    whenever a measured value exists, callers must pass it through instead of
    calling this. Kept only so manual check-ins still produce a score.
    """
    return max(10.0, 65.0 - abs(heart_rate - 65.0))


def derive_sugar(diet_score: float) -> float:
    """
    Sugar-intake proxy from the 1-10 diet score.
    HARDCODED[HC-04]: linear stand-in for a food log. diet_score 10 → ~5 g,
    diet_score 1 → ~95 g.
    """
    return round(105.0 - (diet_score * 10.0), 1)


def _icmr_day(row: Dict[str, Any], static: Dict[str, float]) -> Dict[str, float]:
    """
    Maps one DarpanAI health reading onto the 5 dynamic ICMR features, reusing
    the caller's already-resolved static block.

    Measured values always win over derived proxies: if a wearable supplied a
    real hrv_rmssd or sugar_intake_g, we use it and never fall back.
    """
    heart_rate = _f(row.get("heart_rate"), 72.0)
    diet_score = _f(row.get("diet_score"),  6.0)

    hrv = row.get("hrv_rmssd")
    hrv = _f(hrv, derive_hrv(heart_rate)) if hrv is not None else derive_hrv(heart_rate)

    sugar = row.get("sugar_intake_g")
    sugar = _f(sugar, derive_sugar(diet_score)) if sugar is not None else derive_sugar(diet_score)

    # sleep == 0 from a daytime sync means "not recorded yet", not "no sleep"
    sleep_raw = row.get("sleep")
    sleep_hours = _f(sleep_raw, 7.0) if sleep_raw not in (None, 0) else 7.0

    return {
        **static,
        "sleep_hours":    sleep_hours,
        "steps":          _f(row.get("steps"),        8000.0),
        "sugar_intake_g": sugar,
        "stress_level":   _f(row.get("stress_level"),    4.0),
        "hrv_rmssd":      hrv,
    }


def _f(val: Any, default: float) -> float:
    """float() that tolerates None and junk."""
    if val is None:
        return float(default)
    try:
        return float(val)
    except (TypeError, ValueError):
        return float(default)


def _static_block(snapshot: Dict[str, Any], age: float) -> Dict[str, float]:
    """The 7 static ICMR features, which don't vary across the sequence."""
    return {
        "age":              _f(age,                             35.0),
        "gender":           _f(snapshot.get("gender"),            0.0),
        "bmi":              _f(snapshot.get("bmi"),              23.5),
        "whr":              _f(snapshot.get("whr"),              0.85),
        "fam_diabetes":     _f(snapshot.get("fam_diabetes"),      0.0),
        "fam_cvd":          _f(snapshot.get("fam_cvd"),           0.0),
        "fam_hypertension": _f(snapshot.get("fam_hypertension"),  0.0),
    }


def build_sequence_from_snapshot(snapshot: Dict[str, Any], age: float = 35.0) -> list:
    """
    Converts a single health snapshot into a 30-day sequence by repeating it.

    HARDCODED[HC-05]: tiling one day 30x zeroes every std and trend feature the
    XGBoost layer computes, and gives the transformer nothing temporal to read.
    It is the correct fallback for a brand-new user with one manual check-in,
    but it is NOT the good path — prefer build_sequence_from_history() whenever
    the user has real history. `sequence_source` in predict_risk()'s output
    reports which path actually ran, so the UI never implies 30 days of data
    that don't exist.
    """
    static = _static_block(snapshot, age)
    return [_icmr_day(snapshot, static)] * SEQUENCE_LEN


def build_sequence_from_history(
    history: list,
    snapshot: Dict[str, Any],
    age: float = 35.0,
) -> tuple[list, int]:
    """
    Builds a real 30-day sequence from the user's health_logs history.

    Args:
        history:  readings ordered NEWEST FIRST (as the DB returns them).
        snapshot: the current reading, used for the static block and as the
                  most recent day.
        age:      resolved age.

    Returns (sequence_of_30_days, n_real_days).

    Fewer than 30 real readings are left-padded with the oldest available day
    so the tensor shape holds. n_real_days reports how many are genuine, which
    is what the caller should surface — a 12-day history padded to 30 must not
    be presented as a month of data.
    """
    static = _static_block(snapshot, age)

    # Oldest → newest, so index -1 is today and the 7d-trend features read the
    # right direction. _extract_xgb_features does col[-7:].mean() - col[:7].mean().
    ordered = list(reversed(history))[-SEQUENCE_LEN:]
    days = [_icmr_day(row, static) for row in ordered]

    if not days:
        return build_sequence_from_snapshot(snapshot, age), 0

    n_real = len(days)
    if n_real < SEQUENCE_LEN:
        days = [days[0]] * (SEQUENCE_LEN - n_real) + days

    return days, n_real


def categorize(composite: float) -> str:
    for lo, hi, label in CATEGORY_THRESHOLDS:
        if lo <= composite < hi:
            return label
    return "Critical"


def predict_risk(
    snapshot: Dict[str, Any],
    age: float = 35.0,
    history: list | None = None,
) -> Dict[str, Any]:
    """
    High-level function used by risk_service.py, explain_service.py and
    simulation_service.py — the single entry point for a risk score.

    Args:
        snapshot: current reading + clinical profile (gender/whr/fam_*).
        age:      resolved age.
        history:  optional health_logs rows, NEWEST FIRST. When supplied and
                  non-empty, a real 30-day sequence is built instead of tiling
                  the snapshot, which is what makes the transformer's temporal
                  architecture and XGBoost's std/trend features meaningful.

    Returns the 3 disease risks, the composite, the category, top factors, and
    `sequence_source` / `n_real_days` so callers can be honest about how much
    real history backed the number.
    """
    ensemble = get_ensemble()
    saturated_on_history = False

    if history:
        seq, n_real = build_sequence_from_history(history, snapshot, age)
        sequence_source = "history" if n_real > 1 else "snapshot_tiled"
    else:
        seq, n_real = build_sequence_from_snapshot(snapshot, age), 0
        sequence_source = "snapshot_tiled"

    raw_out, saturated = ensemble.predict_single_checked(seq)

    if saturated and sequence_source == "history":
        # A real 30-day window with enough spread (e.g. a heart rate that
        # swings 72->115, steps 8000->17100) can push the XGBoost heads'
        # engineered features (std/min/max/trend) outside anything they saw
        # in training. The symptom is the heads returning wildly negative or
        # oversized raw values, which np.clip(0,100) then floors/ceilings into
        # a plausible-looking but WRONG number — e.g. an elevated heart rate
        # silently reads as "0% risk, Low" instead of surfacing the failure.
        #
        # The snapshot-tiled sequence (today's reading only, no history-driven
        # std/trend features) doesn't trigger this, so it's the safe fallback.
        # We use it, but we do not pretend nothing happened: sequence_source
        # and the saturation flags stay in the response so this is auditable,
        # not hidden.
        logger.warning(
            "[ensemble] XGBoost heads saturated on history-based sequence — "
            "falling back to snapshot-tiled scoring for this request."
        )
        saturated_on_history = True
        seq = build_sequence_from_snapshot(snapshot, age)
        raw_out, saturated_after_fallback = ensemble.predict_single_checked(seq)
        sequence_source = "snapshot_tiled_after_saturation"
    else:
        saturated_after_fallback = False

    diabetes_risk     = round(raw_out["diabetes_risk"]     * DISEASE_SCALE["diabetes_risk"],     2)
    cvd_risk          = round(raw_out["cvd_risk"]          * DISEASE_SCALE["cvd_risk"],          2)
    hypertension_risk = round(raw_out["hypertension_risk"] * DISEASE_SCALE["hypertension_risk"], 2)

    # Composite score: weighted average (CVD weighted highest for short-term risk)
    composite_risk = round(
        COMPOSITE_WEIGHTS["diabetes_risk"]     * diabetes_risk
        + COMPOSITE_WEIGHTS["cvd_risk"]          * cvd_risk
        + COMPOSITE_WEIGHTS["hypertension_risk"] * hypertension_risk,
        2,
    )

    risk_category = categorize(composite_risk)

    # Build top_risk_factors from which individual risk is highest
    scores = {
        "diabetes":     diabetes_risk,
        "cardiovascular_disease": cvd_risk,
        "hypertension": hypertension_risk,
    }

    # Supplement with lifestyle factors based on snapshot badness
    lifestyle = {}
    heart_rate  = snapshot.get("heart_rate", 72)
    sleep       = snapshot.get("sleep", 7)
    steps       = snapshot.get("steps", 8000)
    stress      = snapshot.get("stress_level", 4)
    diet_score  = snapshot.get("diet_score", 6)
    bmi_val     = snapshot.get("bmi", 23.5)

    if stress > 6:
        lifestyle["high_stress"] = stress / 10
    if sleep < 6:
        lifestyle["poor_sleep"] = (7 - sleep) / 7
    if bmi_val > 27:
        lifestyle["elevated_bmi"] = (bmi_val - 18.5) / 36.5
    if steps < 5000:
        lifestyle["low_activity"] = 1 - (steps / 10000)
    if heart_rate > 90 or heart_rate < 55:
        lifestyle["abnormal_heart_rate"] = abs(heart_rate - 70) / 100
    if diet_score < 5:
        lifestyle["poor_diet"] = 1 - (diet_score / 10)

    all_factors = {**scores, **lifestyle}
    top_risk_factors = sorted(all_factors, key=all_factors.get, reverse=True)[:3]

    return {
        "diabetes_risk":     diabetes_risk,
        "cvd_risk":          cvd_risk,
        "hypertension_risk": hypertension_risk,
        "composite_risk":    composite_risk,
        "risk_category":     risk_category,
        "top_risk_factors":  top_risk_factors,
        # Provenance — how much real history backed this score
        "sequence_source":   sequence_source,
        "n_real_days":       n_real if not saturated_on_history else 0,
        # Saturation disclosure — auditable, never silent
        "model_saturated":      saturated_on_history,
        "saturated_after_fallback": saturated_after_fallback,
    }
