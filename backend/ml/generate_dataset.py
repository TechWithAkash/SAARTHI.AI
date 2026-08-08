"""
Synthetic health dataset generator.
Run: python -m backend.ml.generate_dataset
Outputs: backend/ml/health_dataset.csv
"""
import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)
N = 5000


def generate() -> pd.DataFrame:
    age           = RNG.integers(18, 80, N).astype(float)
    bmi           = RNG.normal(26.5, 5.5, N).clip(15, 55)
    sleep         = RNG.normal(6.5, 1.5, N).clip(2, 12)
    steps         = RNG.normal(6500, 3000, N).clip(0, 25000)
    stress_level  = RNG.integers(1, 11, N).astype(float)
    diet_score    = RNG.integers(1, 11, N).astype(float)
    heart_rate    = RNG.normal(72, 14, N).clip(40, 180)

    # Risk formula — domain-grounded weights
    risk = (
        0.20 * (age / 80)
        + 0.18 * ((bmi - 18.5) / 36.5).clip(0, 1)
        + 0.20 * (1 - sleep / 12)
        + 0.12 * (1 - steps / 25000)
        + 0.16 * (stress_level / 10)
        + 0.08 * (1 - diet_score / 10)
        + 0.06 * ((heart_rate - 40) / 140)
    )

    # Add noise and scale to 0-100
    noise = RNG.normal(0, 0.04, N)
    risk_score = (risk + noise).clip(0, 1) * 100

    df = pd.DataFrame({
        "age":          age,
        "bmi":          bmi.round(1),
        "sleep":        sleep.round(1),
        "steps":        steps.round(0),
        "stress_level": stress_level,
        "diet_score":   diet_score,
        "heart_rate":   heart_rate.round(0),
        "risk_score":   risk_score.round(2),
    })

    out = Path(__file__).parent / "health_dataset.csv"
    df.to_csv(out, index=False)
    print(f"Dataset saved → {out}  ({len(df)} rows)")
    return df


if __name__ == "__main__":
    df = generate()
    print(df.describe().round(2))
