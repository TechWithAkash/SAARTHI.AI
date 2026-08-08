"""
Causal Inference Service — DarpanAI Phase 8.

Uses DoWhy to answer: "What CAUSES this person's elevated risk?"

Approach:
  Rather than running a full causal model on each request (expensive),
  we use a pre-defined causal graph grounded in clinical evidence,
  then estimate Average Treatment Effects (ATE) using the user's
  recent health history as observational data.

Causal graph (directed, domain-grounded):
  stress_level  → heart_rate          (acute stress elevates HR)
  stress_level  → sleep               (stress disrupts sleep)
  sleep         → heart_rate          (poor sleep elevates resting HR)
  sleep         → diet_score          (tired people eat worse)
  diet_score    → bmi                 (diet affects weight)
  bmi           → heart_rate          (obesity elevates resting HR)
  steps         → bmi                 (activity reduces BMI)
  steps         → sleep               (exercise improves sleep)
  heart_rate    → risk_score          (elevated HR drives CV risk)
  stress_level  → risk_score          (direct stress → risk)
  sleep         → risk_score          (poor sleep → risk)
  bmi           → risk_score          (obesity → risk)
  diet_score    → risk_score          (poor diet → risk)
  steps         → risk_score          (inactivity → risk)

For each user we:
  1. Load their last 30–90 health readings as observational data
  2. For each modifiable factor, estimate: ATE of improving it by 1 std
  3. Rank factors by estimated risk reduction
  4. Identify the primary causal chain to the top risk factor
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import warnings

import numpy as np
import pandas as pd

from backend.db.postgres import get_db

warnings.filterwarnings("ignore")

# ── Causal graph ──────────────────────────────────────────────────────────────

CAUSAL_GRAPH_GML = """
graph [
  directed 1
  node [ id "stress_level"  label "stress_level"  ]
  node [ id "sleep"         label "sleep"         ]
  node [ id "steps"         label "steps"         ]
  node [ id "diet_score"    label "diet_score"    ]
  node [ id "bmi"           label "bmi"           ]
  node [ id "heart_rate"    label "heart_rate"    ]
  node [ id "risk_score"    label "risk_score"    ]

  edge [ source "stress_level"  target "heart_rate"  ]
  edge [ source "stress_level"  target "sleep"       ]
  edge [ source "stress_level"  target "risk_score"  ]
  edge [ source "sleep"         target "heart_rate"  ]
  edge [ source "sleep"         target "diet_score"  ]
  edge [ source "sleep"         target "risk_score"  ]
  edge [ source "diet_score"    target "bmi"         ]
  edge [ source "diet_score"    target "risk_score"  ]
  edge [ source "bmi"           target "heart_rate"  ]
  edge [ source "bmi"           target "risk_score"  ]
  edge [ source "steps"         target "bmi"         ]
  edge [ source "steps"         target "sleep"       ]
  edge [ source "steps"         target "risk_score"  ]
  edge [ source "heart_rate"    target "risk_score"  ]
]
"""

# Modifiable treatment variables (age is excluded — not actionable)
TREATMENTS = ["stress_level", "sleep", "steps", "diet_score", "bmi"]

# Whether reducing (True) or increasing (False) the variable improves health
LOWER_IS_BETTER = {
    "stress_level": True,
    "sleep":        False,   # higher sleep = better
    "steps":        False,   # higher steps = better
    "diet_score":   False,   # higher score = better
    "bmi":          True,
}

# Causal chain narratives (primary → mediator → outcome)
CAUSAL_CHAINS = {
    "stress_level": "stress_level → heart_rate → risk_score",
    "sleep":        "sleep → heart_rate & diet_score → risk_score",
    "bmi":          "bmi → heart_rate → risk_score",
    "steps":        "steps → bmi & sleep → risk_score",
    "diet_score":   "diet_score → bmi → risk_score",
    "heart_rate":   "heart_rate → risk_score",
}

# ── History thresholds ────────────────────────────────────────────────────────
# _estimate_ate_linear regresses the outcome on the treatment PLUS 4 confounders
# — 5 predictors. Fitting that on 3 rows is exactly determined: the coefficient
# is arithmetic, not an estimate, and its standard error is undefined. The old
# MIN_HISTORY = 3 therefore let the app assert "causal inference" on data that
# could not support it.
#
# MIN_HISTORY_ATE = 14 is the threshold for making an observational causal
# claim: 5 predictors plus meaningful residual degrees of freedom, and two full
# weeks captures weekday/weekend behavioural variation rather than a single
# week's idiosyncrasy. Below it we fall back to the honest SHAP-prior path and
# label it as such. Garmin backfill (BP-6) clears this bar in one sync.
MIN_HISTORY_ATE = 14

# Absolute floor for attempting any regression at all.
MIN_ROWS_REGRESSION = 5

# Retained for callers/tests that referenced the old name; the join and
# data-assembly steps still use a low bar, only the CAUSAL CLAIM needs 14.
MIN_HISTORY = MIN_ROWS_REGRESSION


def _build_causal_graph(profile: dict) -> str:
    """
    Dynamically construct the causal graph GML based on the user's clinical profile.
    All users share the core graph. Additional edges are added based on:
      - Family history of diabetes / CVD / hypertension
      - Age (older patients: sleep and stress have stronger mediating roles)
      - BMI level (obese patients: diet → BMI pathway is primary)
    """
    age            = float(profile.get("age", 35))
    fam_diabetes   = bool(profile.get("fam_diabetes", 0))
    fam_cvd        = bool(profile.get("fam_cvd", 0))
    fam_hypert     = bool(profile.get("fam_hypertension", 0))
    bmi            = float(profile.get("bmi", 23.5))
    diabetes_risk  = float(profile.get("diabetes_risk", 0))
    cvd_risk       = float(profile.get("cvd_risk", 0))

    # Core edges — always present
    edges = [
        ('stress_level', 'heart_rate'),
        ('stress_level', 'sleep'),
        ('stress_level', 'risk_score'),
        ('sleep',        'heart_rate'),
        ('sleep',        'diet_score'),
        ('sleep',        'risk_score'),
        ('diet_score',   'bmi'),
        ('diet_score',   'risk_score'),
        ('bmi',          'heart_rate'),
        ('bmi',          'risk_score'),
        ('steps',        'bmi'),
        ('steps',        'sleep'),
        ('steps',        'risk_score'),
        ('heart_rate',   'risk_score'),
    ]

    # Family history of diabetes → diet becomes a stronger direct driver
    if fam_diabetes or diabetes_risk > 30:
        edges.append(('diet_score', 'stress_level'))   # sugar crashes drive stress
        edges.append(('sleep',      'bmi'))             # sleep deprivation → weight gain

    # Family history of CVD → heart_rate pathway becomes dominant
    if fam_cvd or cvd_risk > 30:
        edges.append(('stress_level', 'bmi'))           # chronic stress → visceral fat
        edges.append(('steps',        'heart_rate'))    # inactivity directly elevates HR

    # Family history of hypertension → stress and diet are primary levers
    if fam_hypert:
        edges.append(('diet_score', 'heart_rate'))      # sodium/diet directly raises BP
        edges.append(('stress_level', 'diet_score'))    # stress-eating loop

    # Older patients (>50): sleep and stress have compounding mediator effects
    if age > 50:
        edges.append(('sleep', 'steps'))                # fatigue reduces activity
        edges.append(('bmi',   'stress_level'))         # obesity drives anxiety

    # Obese patients: diet-BMI pathway is the primary axis
    if bmi > 28:
        edges.append(('steps', 'diet_score'))           # active people eat better

    # Deduplicate
    unique_edges = list(dict.fromkeys(edges))

    # Build GML nodes
    nodes = ['stress_level', 'sleep', 'steps', 'diet_score', 'bmi', 'heart_rate', 'risk_score']
    node_block = "\n".join(
        f'  node [ id "{n}" label "{n}" ]' for n in nodes
    )
    edge_block = "\n".join(
        f'  edge [ source "{s}" target "{t}" ]' for s, t in unique_edges
    )
    return f"graph [\n  directed 1\n{node_block}\n{edge_block}\n]\n"


# ── Statistical ATE estimation ────────────────────────────────────────────────

def _estimate_ate_linear(
    df: pd.DataFrame,
    treatment: str,
    outcome: str = "risk_score",
) -> Optional[float]:
    """
    Estimate Average Treatment Effect using linear regression with confounders.
    This is the backdoor adjustment formula (DoWhy LinearDML equivalent)
    but implemented directly to avoid DoWhy's sklearn version conflicts.

    Returns: expected change in risk_score per 1-std improvement in treatment.
    """
    try:
        from sklearn.linear_model import LinearRegression

        confounders = [c for c in TREATMENTS if c != treatment and c in df.columns]
        all_cols = [treatment] + confounders

        df_clean = df[all_cols + [outcome]].dropna()
        # Need more rows than predictors, or the fit is degenerate
        if len(df_clean) < max(MIN_ROWS_REGRESSION, len(all_cols) + 2):
            return None

        X = df_clean[all_cols].values
        y = df_clean[outcome].values

        model = LinearRegression().fit(X, y)
        # Coefficient for the treatment variable = ATE per unit
        treatment_idx = all_cols.index(treatment)
        coef = model.coef_[treatment_idx]

        # Scale to "1 std improvement" effect
        std = df_clean[treatment].std()
        if std < 1e-6:
            return None

        # For "lower is better" variables, improvement = reduce by 1 std → negate
        improvement_direction = -1 if LOWER_IS_BETTER[treatment] else +1
        ate = coef * std * improvement_direction   # negative = risk goes down = good

        return round(float(ate), 3)

    except Exception as e:
        print(f"[causal] linear ATE failed for {treatment}: {type(e).__name__}: {e}")
        return None


def _estimate_with_dowhy(
    df: pd.DataFrame,
    treatment: str,
    outcome: str = "risk_score",
    causal_graph: str = None,
) -> tuple[Optional[float], str]:
    """
    DoWhy causal estimation using the backdoor criterion, on the dynamically
    built user-specific causal graph.

    Returns (ate, estimator) where estimator names what ACTUALLY produced the
    number: "dowhy_backdoor", "linear_backdoor", or "none".

    This return shape exists because the previous version silently swallowed
    DoWhy failures and fell back to plain linear regression, while the caller
    still labelled the result "dowhy_backdoor". DoWhy raising on sklearn
    version conflicts is common here, so that label was frequently a lie.
    """
    try:
        import dowhy
        from dowhy import CausalModel

        confounders = [c for c in TREATMENTS if c != treatment and c in df.columns]
        df_clean = df[[treatment] + confounders + [outcome]].dropna()

        if len(df_clean) < MIN_ROWS_REGRESSION:
            return None, "none"

        # Binarize treatment (above/below median = treated/control)
        median_val = df_clean[treatment].median()
        df_binary = df_clean.copy()
        df_binary[treatment] = (df_clean[treatment] > median_val).astype(int)

        model = CausalModel(
            data=df_binary,
            treatment=treatment,
            outcome=outcome,
            graph=causal_graph,
        )

        identified = model.identify_effect(proceed_when_unidentifiable=True)
        estimate   = model.estimate_effect(
            identified,
            method_name="backdoor.linear_regression",
            control_value=0,
            treatment_value=1,
        )

        ate_raw = float(estimate.value)

        # Scale: binary median split → "1 std improvement" direction
        std = df_clean[treatment].std()
        if std < 1e-6:
            return None, "none"

        improvement_direction = -1 if LOWER_IS_BETTER[treatment] else +1
        # Binary ATE is already in risk_score units; scale by direction
        ate = ate_raw * improvement_direction
        return round(ate, 3), "dowhy_backdoor"

    except Exception as e:
        # Log rather than swallow: DoWhy failing on a sklearn version mismatch
        # is the common case here and was previously invisible.
        print(f"[causal] dowhy failed for {treatment}: {type(e).__name__}: {e}")
        fallback = _estimate_ate_linear(df, treatment, outcome)
        return fallback, ("linear_backdoor" if fallback is not None else "none")


# ── Main service ──────────────────────────────────────────────────────────────

async def run_causal(
    user_id: str,
    log_id:  str,
    normalized: dict,
) -> Dict[str, Any]:
    pool = get_db()

    async with pool.acquire() as conn:
        # One row per calendar day, not per submission — a burst of repeated
        # manual check-ins on the same day would otherwise count as that many
        # separate observations, distorting the regression this feeds (see the
        # matching comment in risk_service.py's history query).
        log_rows = await conn.fetch(
            """
            SELECT DISTINCT ON ((timestamp AT TIME ZONE 'UTC')::date)
                   log_id, heart_rate, steps, sleep, bmi, stress_level, diet_score
            FROM health_logs
            WHERE user_id = $1
            ORDER BY (timestamp AT TIME ZONE 'UTC')::date DESC, timestamp DESC
            LIMIT 90
            """,
            user_id,
        )

        # Fetch corresponding risk scores — same per-day dedup, so a day with
        # multiple recomputes doesn't outnumber its matching health_logs day.
        risk_rows = await conn.fetch(
            """
            SELECT DISTINCT ON ((timestamp AT TIME ZONE 'UTC')::date)
                   log_id, risk_score
            FROM risk_scores
            WHERE user_id = $1
            ORDER BY (timestamp AT TIME ZONE 'UTC')::date DESC, timestamp DESC
            LIMIT 90
            """,
            user_id,
        )

        # Fetch clinical profile (age, family history) for dynamic causal graph
        user_row = await conn.fetchrow(
            """
            SELECT age, fam_diabetes, fam_cvd, fam_hypertension
            FROM users WHERE user_id = $1
            """,
            user_id,
        )

        # Fetch latest risk row for SHAP contributions
        latest_risk = await conn.fetchrow(
            """
            SELECT shap_contributions
            FROM risk_scores
            WHERE user_id = $1
            ORDER BY timestamp DESC LIMIT 1
            """,
            user_id,
        )

    logs      = [dict(r) for r in log_rows]
    risk_docs = [dict(r) for r in risk_rows]

    # Build profile dict for dynamic graph
    profile = {}
    if user_row:
        profile["age"]             = user_row["age"] or 35
        profile["fam_diabetes"]    = user_row["fam_diabetes"] or 0
        profile["fam_cvd"]         = user_row["fam_cvd"] or 0
        profile["fam_hypertension"]= user_row["fam_hypertension"] or 0
    if normalized:
        profile["bmi"] = normalized.get("bmi", 23.5)
    if latest_risk and latest_risk["shap_contributions"]:
        shap = json.loads(latest_risk["shap_contributions"])
        profile["diabetes_risk"] = shap.get("diabetes_risk", 0)
        profile["cvd_risk"]      = shap.get("cvd_risk", 0)

    # Build dynamic causal graph for this user
    dynamic_graph = _build_causal_graph(profile)

    # Not enough history — return graph-based priors
    if len(logs) < MIN_HISTORY_ATE or len(risk_docs) < MIN_HISTORY_ATE:
        return await _causal_from_shap_priors(
            user_id, log_id, normalized, pool,
            reason=(
                f"{len(logs)} health logs and {len(risk_docs)} risk scores on record; "
                f"need {MIN_HISTORY_ATE} of each for an observational ATE"
            ),
        )

    # Build DataFrame: join logs + risk_scores by log_id
    risk_map = {r["log_id"]: r["risk_score"] for r in risk_docs}

    rows = []
    for log in logs:
        lid = log.get("log_id")
        if lid not in risk_map:
            continue
        # health_logs is now flat — access columns directly
        row = {
            "risk_score":   risk_map[lid],
            "heart_rate":   log.get("heart_rate"),
            "sleep":        log.get("sleep"),
            "steps":        log.get("steps"),
            "stress_level": log.get("stress_level"),
            "diet_score":   log.get("diet_score"),
            "bmi":          log.get("bmi"),
        }
        rows.append(row)

    df = pd.DataFrame(rows).dropna()

    # An observational causal claim needs enough rows to support the regression.
    # Below MIN_HISTORY_ATE we do NOT assert causal inference — we fall back to
    # the SHAP-prior path and label it honestly.
    if len(df) < MIN_HISTORY_ATE:
        return await _causal_from_shap_priors(
            user_id, log_id, normalized, pool,
            reason=f"only {len(df)} joined observations; need {MIN_HISTORY_ATE} for an ATE",
        )

    # Estimate ATE for each modifiable treatment
    effects: Dict[str, float] = {}
    estimators: Dict[str, str] = {}
    for treatment in TREATMENTS:
        if treatment not in df.columns:
            continue
        ate, estimator = _estimate_with_dowhy(df, treatment, causal_graph=dynamic_graph)
        if ate is not None:
            effects[treatment] = ate   # negative = risk-reducing intervention
            estimators[treatment] = estimator

    return await _persist_causal(
        user_id, log_id, normalized, effects, df, pool, estimators=estimators,
    )


async def _causal_from_shap_priors(
    user_id: str,
    log_id: str,
    normalized: dict,
    pool,
    reason: str = "insufficient history",
) -> Dict[str, Any]:
    """
    When insufficient history exists, infer effect PRIORS from SHAP values and
    the domain causal graph.

    These are NOT causal effects. They are attribution-derived priors that
    indicate which factors the model currently weights most, signed by whether
    improving the factor should help. Consumers must treat them as weaker
    evidence — `method` is "shap_prior" and every factor is tagged
    estimator="shap_prior" so nothing downstream can mistake one for an ATE.
    """
    async with pool.acquire() as conn:
        shap_row = await conn.fetchrow(
            """
            SELECT shap_contributions
            FROM risk_scores
            WHERE user_id = $1 AND log_id = $2
            LIMIT 1
            """,
            user_id,
            log_id,
        )

    # shap_contributions is JSONB — asyncpg returns it as a string
    shap = {}
    if shap_row and shap_row["shap_contributions"]:
        shap = json.loads(shap_row["shap_contributions"])

    # Effect size ≈ -|SHAP| (higher SHAP → more modifiable risk)
    effects = {}
    for feat in TREATMENTS:
        sv = shap.get(feat, 0.0)
        direction = -1 if LOWER_IS_BETTER.get(feat, True) else +1
        # Improving the factor should reverse its SHAP contribution
        effects[feat] = round(-abs(sv) * direction, 3) if sv else 0.0

    return await _persist_causal(
        user_id, log_id, normalized, effects, None, pool,
        estimators={f: "shap_prior" for f in effects},
        fallback_reason=reason,
    )


async def _persist_causal(
    user_id: str,
    log_id: str,
    normalized: dict,
    effects: Dict[str, float],
    df: Optional[pd.DataFrame],
    pool,
    estimators: Optional[Dict[str, str]] = None,
    fallback_reason: Optional[str] = None,
) -> Dict[str, Any]:
    estimators = estimators or {}

    if not effects:
        primary_cause  = "stress_level"
        causal_chain   = CAUSAL_CHAINS["stress_level"]
        ranked_factors = []
    else:
        # Rank by most risk-reducing (most negative ATE = biggest benefit from improving)
        ranked_factors = sorted(
            [{
                "factor":    k,
                "ate":       v,
                "chain":     CAUSAL_CHAINS.get(k, k),
                # Per-factor provenance: which estimator actually produced this
                "estimator": estimators.get(k, "unknown"),
            } for k, v in effects.items()],
            key=lambda x: x["ate"],   # most negative first
        )
        primary_cause = ranked_factors[0]["factor"] if ranked_factors else "stress_level"
        causal_chain  = CAUSAL_CHAINS.get(primary_cause, primary_cause)

    now = datetime.now(timezone.utc)

    # Overall method reflects what ACTUALLY ran, not what we hoped would run.
    used = {e for e in estimators.values() if e not in ("none", "unknown")}
    if not used:
        method = "none"
    elif used == {"shap_prior"}:
        method = "shap_prior"
    elif used == {"dowhy_backdoor"}:
        method = "dowhy_backdoor"
    elif used == {"linear_backdoor"}:
        method = "linear_backdoor"
    else:
        method = "mixed"

    result = {
        "user_id":        user_id,
        "log_id":         log_id,
        "timestamp":      now,
        "method":         method,
        "estimators":     estimators,
        "is_causal":      method in ("dowhy_backdoor", "linear_backdoor", "mixed"),
        "n_observations": len(df) if df is not None else 0,
        "min_observations_for_ate": MIN_HISTORY_ATE,
        "causal_effects": effects,
        "ranked_factors": ranked_factors,
        "primary_cause":  primary_cause,
        "causal_chain":   causal_chain,
    }
    if fallback_reason:
        result["fallback_reason"] = fallback_reason

    async with pool.acquire() as conn:
        # Insert causal result
        await conn.execute(
            """
            INSERT INTO causal_results (user_id, ranked_factors, primary_cause, causal_chain, timestamp)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id,
            json.dumps(ranked_factors),   # JSONB → serialise
            primary_cause,
            causal_chain,
            now,
        )

        # Update the risk_score row with causal chain
        await conn.execute(
            """
            UPDATE risk_scores
            SET causal_chain = $1, primary_cause = $2
            WHERE user_id = $3 AND log_id = $4
            """,
            causal_chain,
            primary_cause,
            user_id,
            log_id,
        )

    return result
