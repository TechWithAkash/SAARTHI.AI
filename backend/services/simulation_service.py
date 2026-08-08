"""
Simulation Engine — trajectory projection over the live DarpanEnsemble.

Previously this loaded the retired 7-feature risk_model.pkl, so the simulation
curves and the dashboard's risk score came from two different models and could
disagree. Both now run through ensemble_service.predict_risk(), so a scenario
that says "day 120 = 24.1" is on the same scale and from the same model as the
headline number.

Scenarios:
  current  — no behaviour change (habit decay + drift)
  improved — sustained realistic deltas, phased in on an adherence curve
  optimal  — every modifiable factor at its clinical target, never worse than now

ON TILING: each checkpoint asks "what is this person's risk if they sustain
this state for a month?", so repeating the counterfactual day across the 30-day
window is the semantically correct input here — unlike scoring a real user,
where tiling one reading fakes history it doesn't have (HC-05).
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import numpy as np

from backend.db.postgres import get_db
from backend.services.ensemble_service import DISEASES, SEQUENCE_LEN, predict_risk

# Checkpoints (days) at which we compute risk
TIMELINE = [0, 15, 30, 45, 60, 90, 120]

# The model reads a trailing 30-day window; each checkpoint is scored on its own
SEQUENCE_WINDOW = SEQUENCE_LEN

# Clinical targets for the optimal scenario
OPTIMAL_TARGETS = {
    "sleep":        8.0,
    "steps":        10000,
    "stress_level": 3,
    "diet_score":   8,
    "heart_rate":   65,
    "bmi":          22.5,
}

# Default "improved" deltas. Callers may override per-request (see
# simulate_overrides) — these are the defaults, not the only option.
IMPROVED_DELTAS = {
    "sleep":        +2.0,
    "steps":        +3000,
    "stress_level": -2.0,
    "diet_score":   +1.5,
}

# Physiological bounds for clamping simulated states
BOUNDS = {
    "heart_rate":   (40,  200),
    "steps":        (0,   20000),
    "sleep":        (0,   12),
    "bmi":          (15,  50),
    "stress_level": (1,   10),
    "diet_score":   (1,   10),
}

# Which snapshot keys a scenario is allowed to move
MODIFIABLE = ("sleep", "steps", "stress_level", "diet_score", "heart_rate", "bmi")


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _clamp_field(field: str, val: float) -> float:
    lo, hi = BOUNDS.get(field, (0.0, 1e9))
    return _clamp(val, lo, hi)


# ── Shared what-if primitive ──────────────────────────────────────────────────

def simulate_overrides(
    base_snapshot: Dict[str, Any],
    age: float,
    overrides: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Scores one counterfactual: the base snapshot with `overrides` applied and
    sustained for a month.

    This is the single what-if primitive — the intended entry point for any
    sensitivity analysis (tornado plot, inverse solver) so those never
    re-implement scoring. Runs in ~5 ms, so brute-force sweeps are viable.

    The counterfactual is scored on a 30-day window that ramps linearly from
    today's state to the target rather than 30 identical days, for the same
    reason as _trailing_window(): the XGBoost threshold-day counters otherwise
    make the answer jump discontinuously the moment a slider crosses 4,000
    steps or 7/10 stress. A ramp keeps the interactive response monotone.
    """
    target = dict(base_snapshot)
    for field, value in (overrides or {}).items():
        if field in MODIFIABLE:
            target[field] = _clamp_field(field, float(value))

    # newest first: index 0 is fully at target, index 29 is today's state
    window = []
    for offset in range(SEQUENCE_WINDOW):
        frac = (SEQUENCE_WINDOW - 1 - offset) / (SEQUENCE_WINDOW - 1)
        day = dict(target)
        for field in MODIFIABLE:
            if field in base_snapshot and field in target:
                start, end = float(base_snapshot[field]), float(target[field])
                day[field] = _clamp_field(field, start + frac * (end - start))
        window.append(day)

    return predict_risk(window[0], age=age, history=window)


def _targets_for(base: Dict[str, float], scenario: str) -> Dict[str, float]:
    """The end-state each scenario converges toward."""
    if scenario == "improved":
        return {
            k: _clamp_field(k, base.get(k, 5) + v)
            for k, v in IMPROVED_DELTAS.items()
        }
    if scenario == "optimal":
        improved_finals = {
            k: _clamp_field(k, base.get(k, 5) + v)
            for k, v in IMPROVED_DELTAS.items()
        }
        # Never worse than today, at least as good as `improved`, ideally clinical
        return {
            "sleep":        max(OPTIMAL_TARGETS["sleep"],        improved_finals.get("sleep", base["sleep"]),           base["sleep"]),
            "steps":        max(OPTIMAL_TARGETS["steps"],        improved_finals.get("steps", base["steps"]),           base["steps"]),
            "diet_score":   max(OPTIMAL_TARGETS["diet_score"],   improved_finals.get("diet_score", base["diet_score"]), base["diet_score"]),
            "stress_level": min(OPTIMAL_TARGETS["stress_level"], improved_finals.get("stress_level", base["stress_level"]), base["stress_level"]),
            "heart_rate":   min(OPTIMAL_TARGETS["heart_rate"],   base["heart_rate"]),
        }
    return {}


def _state_at(base: Dict[str, float], scenario: str, targets: Dict[str, float], day: float) -> Dict[str, float]:
    """
    The user's state on a given day of a scenario — a continuous function of
    `day`, which is what lets us build a smooth trailing window below.
    """
    state = dict(base)
    if day <= 0:
        return state

    if scenario == "current":
        # Habit decay: without intervention, metrics drift the wrong way
        t = day / 120.0
        state["sleep"]        = _clamp_field("sleep",        base["sleep"]        - t * 0.8)
        state["steps"]        = _clamp_field("steps",        base["steps"]        - t * 800)
        state["stress_level"] = _clamp_field("stress_level", base["stress_level"] + t * 1.2)
        state["diet_score"]   = _clamp_field("diet_score",   base["diet_score"]   - t * 0.5)
        state["heart_rate"]   = _clamp_field("heart_rate",   base["heart_rate"]   + t * 5.0)
        return state

    # Sigmoid adherence ramp — habits form gradually, not overnight
    midpoint  = 20   if scenario == "improved" else 15
    steepness = 0.15 if scenario == "improved" else 0.20
    adherence = 1 / (1 + np.exp(-steepness * (day - midpoint)))

    for field, target in targets.items():
        state[field] = _clamp_field(field, base[field] + adherence * (target - base[field]))

    if scenario == "improved":
        # HR responds to sustained activity + sleep improvement.
        # BMI is deliberately NOT moved here: 4 months of better sleep and
        # +3k steps/day does not reliably move BMI, and pretending it does was
        # inflating the projected reduction.
        state["heart_rate"] = _clamp_field("heart_rate", base["heart_rate"] - adherence * 8.0)
    else:
        # Optimal: slow realistic BMI reduction, max ~0.5 units per 30 days
        max_reduction = (day / 30) * 0.5
        state["bmi"] = min(
            _clamp(base["bmi"] - max_reduction, OPTIMAL_TARGETS["bmi"], base["bmi"]),
            base["bmi"],
        )
    return state


def _trailing_window(base: Dict[str, float], scenario: str, targets: Dict[str, float], day: int) -> List[Dict[str, float]]:
    """
    The 30 days leading UP TO `day`, newest first — the window shape the model
    was trained on.

    Why this matters: the XGBoost layer counts threshold days (`low_steps_days`
    = days under 4,000 steps, `high_stress_days` = days over 7/10). If we score
    a checkpoint by repeating that single day 30 times, those counts can only
    ever be 0 or 30, so crossing a threshold makes the projection fall off a
    cliff — the earlier version showed a 71% drop between day 15 and day 30
    purely from that artifact. Scoring a real trailing window produces the
    intermediate counts a genuine transition would have, so the curve is smooth
    and the projected benefit is believable.
    """
    return [
        _state_at(base, scenario, targets, day - offset)
        for offset in range(SEQUENCE_WINDOW)
    ]


# ── Credibility cap on projected improvement ──────────────────────────────────
# The ensemble was trained on ICMR cohorts and extrapolates badly when handed an
# idealised lifestyle state: raw meta-learner output for CVD and hypertension
# goes NEGATIVE and clips to 0.0, i.e. the model claims a 47-year-old with
# BMI 29 and family history of hypertension can reach zero risk in 45 days by
# sleeping more. That is a model artefact, not a finding, and presenting it
# would be indefensible.
#
# So we cap the projected *relative* reduction at a conservative, cited ceiling.
# Anchor: the Diabetes Prevention Program (Knowler et al., NEJM 2002;346:393)
# achieved a 58% reduction in diabetes INCIDENCE with intensive lifestyle
# intervention over a mean 2.8 years; Look AHEAD (NEJM 2013;369:145) found no
# significant reduction in cardiovascular events over ~9.6 years. Over a
# 120-day horizon, 30% is therefore already generous.
#
# The uncapped model output is preserved in `raw_uncapped` so nothing is hidden.
MAX_REDUCTION_FRACTION = 0.30

REDUCTION_CAP_CITATION = (
    "Projected reduction capped at 30% of baseline over 120 days. The ensemble's "
    "raw output saturates (clips at 0) for idealised lifestyle states, which is a "
    "model artefact. Cap anchored on DPP (Knowler et al., NEJM 2002) — 58% "
    "reduction in diabetes incidence over 2.8 years of intensive intervention — "
    "and Look AHEAD (NEJM 2013), which found no significant CV event reduction. "
    "Uncapped values are retained in raw_uncapped."
)


def _cap_trajectory(baseline: float, values: List[float]) -> tuple[List[float], bool]:
    """
    Floors a trajectory at (1 - MAX_REDUCTION_FRACTION) x baseline.
    Returns the capped series and whether the cap actually bound anywhere.
    """
    floor = baseline * (1.0 - MAX_REDUCTION_FRACTION)
    capped = [round(max(v, floor), 1) for v in values]
    was_capped = any(c > v + 1e-9 for c, v in zip(capped, values))
    return capped, was_capped


def _run_all_scenarios(base: Dict[str, float], age: float) -> Dict[str, Any]:
    """
    Blocking: 3 scenarios x 7 checkpoints = 21 ensemble calls (~1 s on M4 CPU).
    Callers must wrap this in asyncio.to_thread.
    """
    raw_composite: Dict[str, List[float]] = {}
    raw_disease: Dict[str, Dict[str, List[float]]] = {}
    saturated: List[str] = []

    for scenario in ("current", "improved", "optimal"):
        targets = _targets_for(base, scenario)
        results = []
        for day in TIMELINE:
            window = _trailing_window(base, scenario, targets, day)
            # window[0] is the checkpoint day; pass it as both the snapshot
            # (for the static block) and as newest-first history.
            results.append(predict_risk(window[0], age=age, history=window))

        raw_composite[scenario] = [round(r["composite_risk"], 2) for r in results]
        raw_disease[scenario] = {
            disease: [round(r[disease], 2) for r in results] for disease in DISEASES
        }
        # A disease pinned at exactly 0 or 100 means the meta-learner clipped
        for disease, series in raw_disease[scenario].items():
            if any(v <= 0.0 or v >= 100.0 for v in series):
                saturated.append(f"{scenario}:{disease}")

    # Cap against each series' own day-0 value (the user's real current state)
    composite: Dict[str, List[float]] = {}
    by_disease: Dict[str, Dict[str, List[float]]] = {}
    cap_bound = False

    for scenario in ("current", "improved", "optimal"):
        c, hit = _cap_trajectory(raw_composite[scenario][0], raw_composite[scenario])
        composite[scenario] = c
        cap_bound = cap_bound or hit

        by_disease[scenario] = {}
        for disease, series in raw_disease[scenario].items():
            d, hit_d = _cap_trajectory(series[0], series)
            by_disease[scenario][disease] = d
            cap_bound = cap_bound or hit_d

    return {
        "composite":   composite,
        "by_disease":  by_disease,
        "raw_uncapped": {"composite": raw_composite, "by_disease": raw_disease},
        "capped":       cap_bound,
        "saturated":    sorted(set(saturated)),
    }


async def run_simulation(
    user_id: str,
    log_id: str,
    normalized: dict,
    risk_score: float,
) -> Dict[str, Any]:
    pool = get_db()

    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """
            SELECT age, gender, whr, fam_diabetes, fam_cvd, fam_hypertension
            FROM users WHERE user_id = $1
            """,
            user_id,
        )
        log = await conn.fetchrow(
            """
            SELECT heart_rate, sleep, steps, bmi, stress_level, diet_score, extras
            FROM health_logs WHERE log_id = $1
            """,
            log_id,
        )

    age = float(user["age"]) if (user and user["age"] is not None) else 35.0
    base = _build_base(log, normalized, user)

    projected = await asyncio.to_thread(_run_all_scenarios, base, age)

    composite  = projected["composite"]
    by_disease = projected["by_disease"]

    current, improved, optimal = composite["current"], composite["improved"], composite["optimal"]

    # Reduction is measured against where the user ends up doing NOTHING, not
    # against today. That's the honest counterfactual: the benefit of acting is
    # the gap versus the do-nothing trajectory at the same point in time.
    do_nothing_end = current[-1] if current[-1] > 0 else 1.0
    baseline_today = current[0] if current[0] > 0 else 1.0

    projected_risk_reduction = {
        "improved":                round((do_nothing_end - improved[-1]) / do_nothing_end * 100, 1),
        "optimal":                 round((do_nothing_end - optimal[-1])  / do_nothing_end * 100, 1),
        "improved_vs_today":       round((baseline_today - improved[-1]) / baseline_today * 100, 1),
        "optimal_vs_today":        round((baseline_today - optimal[-1])  / baseline_today * 100, 1),
        "improved_absolute_pts":   round(current[-1] - improved[-1], 1),
        "optimal_absolute_pts":    round(current[-1] - optimal[-1], 1),
    }

    scenarios = {
        "current":    current,
        "improved":   improved,
        "optimal":    optimal,
        "by_disease": by_disease,
    }
    scenario_assumptions = {
        "improved": {
            "sleep_increase_hours": IMPROVED_DELTAS["sleep"],
            "steps_increase":       IMPROVED_DELTAS["steps"],
            "stress_reduction":     abs(IMPROVED_DELTAS["stress_level"]),
            "diet_score_increase":  IMPROVED_DELTAS["diet_score"],
            "note": "BMI held constant — sleep and activity changes alone do not reliably move it over 120 days.",
        },
        "optimal": OPTIMAL_TARGETS,
        "reduction_basis": "percent vs the day-120 do-nothing trajectory",
        "model": "darpan_ensemble_v2_12feature",
        "scoring": "each checkpoint scored on its own trailing 30-day window",
        # Honesty metadata — surfaced so the UI can disclose it rather than
        # quietly presenting a capped curve as a raw model output.
        "reduction_cap":     MAX_REDUCTION_FRACTION,
        "cap_applied":       projected["capped"],
        "cap_rationale":     REDUCTION_CAP_CITATION,
        "saturated_outputs": projected["saturated"],
    }

    generated_at = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO simulations (
                user_id, based_on_log_id, scenarios, timeline_days,
                projected_risk_reduction, scenario_assumptions, generated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            user_id, log_id,
            json.dumps(scenarios),
            json.dumps(TIMELINE),
            json.dumps(projected_risk_reduction),
            json.dumps(scenario_assumptions),
            generated_at,
        )

    return {
        "user_id":                  user_id,
        "based_on_log_id":          log_id,
        "generated_at":             generated_at,
        "timeline_days":            TIMELINE,
        "scenarios":                scenarios,
        "scenario_assumptions":     scenario_assumptions,
        "projected_risk_reduction": projected_risk_reduction,
    }


# ── What-if endpoint support ───────────────────────────────────────────────────

async def run_whatif(user_id: str, overrides: Dict[str, float]) -> Dict[str, Any]:
    """
    Scores one user-specified counterfactual against the user's current state.

    Backs the interactive predictor: "if I walked 12,000 steps and slept 8h,
    what happens to my risk?" Returns both states plus the deltas, per disease.
    """
    pool = get_db()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """
            SELECT age, gender, whr, fam_diabetes, fam_cvd, fam_hypertension
            FROM users WHERE user_id = $1
            """,
            user_id,
        )
        log = await conn.fetchrow(
            """
            SELECT heart_rate, sleep, steps, bmi, stress_level, diet_score, extras
            FROM health_logs
            WHERE user_id = $1
            ORDER BY timestamp DESC LIMIT 1
            """,
            user_id,
        )

    if log is None:
        raise ValueError("No health data for this user yet — submit a check-in first.")

    age  = float(user["age"]) if (user and user["age"] is not None) else 35.0
    base = _build_base(log, None, user)

    applied = {k: float(v) for k, v in overrides.items() if k in MODIFIABLE}

    baseline, counterfactual = await asyncio.to_thread(
        lambda: (
            simulate_overrides(base, age, None),
            simulate_overrides(base, age, applied),
        )
    )

    keys = ["composite_risk"] + DISEASES
    # simulate_overrides() -> predict_risk() already computes model_saturated
    # for both calls; this endpoint used to discard it before returning,
    # which meant a saturated counterfactual (e.g. a disease pinned at exactly
    # 0.0 — the same XGBoost-extrapolation failure mode fixed for the main
    # risk score) would render as a confident number with no warning the
    # instant this became a real interactive UI. Surfaced the same way the
    # dashboard already does, not swallowed here.
    saturated = bool(baseline.get("model_saturated") or counterfactual.get("model_saturated"))
    return {
        "user_id":        user_id,
        "baseline_state": {k: base.get(k) for k in MODIFIABLE},
        "applied":        applied,
        "rejected":       sorted(set(overrides) - set(applied)),
        "baseline":       {k: baseline[k] for k in keys},
        "counterfactual": {k: counterfactual[k] for k in keys},
        "delta":          {k: round(counterfactual[k] - baseline[k], 2) for k in keys},
        "risk_category":  counterfactual["risk_category"],
        "model_saturated": saturated,
        "note": (
            "Projects sustaining this state for 30 days. Deltas are model "
            "output differences, not a clinical guarantee."
            + (" Model confidence is reduced for this input — treat the numbers as indicative." if saturated else "")
        ),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

_NORM_BOUNDS = BOUNDS


def _pj(val, default):
    if val is None:
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _build_base(log, normalized: Optional[dict], user) -> Dict[str, float]:
    """
    Assembles the base snapshot for simulation: vitals + clinical profile.
    Prefers the real log row; falls back to denormalizing.
    """
    if log is not None:
        base = {
            "heart_rate":   float(log["heart_rate"]   if log["heart_rate"]   is not None else 72),
            "sleep":        float(log["sleep"] if log["sleep"] not in (None, 0) else 7),
            "steps":        float(log["steps"]        if log["steps"]        is not None else 8000),
            "bmi":          float(log["bmi"]          if log["bmi"]          is not None else 23.5),
            "stress_level": float(log["stress_level"] if log["stress_level"] is not None else 4),
            "diet_score":   float(log["diet_score"]   if log["diet_score"]   is not None else 6),
        }
        extras = _pj(log["extras"] if "extras" in log.keys() else None, {}) or {}
        for key in ("hrv_rmssd", "sugar_intake_g"):
            if extras.get(key) is not None:
                base[key] = float(extras[key])
    else:
        src = normalized or {}
        base = {
            field: round(lo + src.get(field, 0.5) * (hi - lo), 2)
            for field, (lo, hi) in _NORM_BOUNDS.items()
        }

    gender_raw = user["gender"] if user else None
    base.update({
        "gender":           1 if str(gender_raw).lower() in ("male", "m", "1") else 0,
        "whr":              float(user["whr"]) if (user and user["whr"] is not None) else 0.85,
        "fam_diabetes":     int(user["fam_diabetes"])     if (user and user["fam_diabetes"]     is not None) else 0,
        "fam_cvd":          int(user["fam_cvd"])          if (user and user["fam_cvd"]          is not None) else 0,
        "fam_hypertension": int(user["fam_hypertension"]) if (user and user["fam_hypertension"] is not None) else 0,
    })
    return base
