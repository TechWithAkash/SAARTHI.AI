import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.models.health import HealthDataInput, HealthDataResponse
from backend.services.ingestion_service import ingest
from backend.services.anomaly_service import detect_anomalies
from backend.services.risk_service import compute_risk
from backend.services.explain_service import explain_risk
from backend.services.causal_service import run_causal
from backend.services.simulation_service import run_simulation
from backend.services.cognitive_agent_service import run_cognitive_agent
from backend.services.telegram_service import send_health_alert, send_anomaly_alert
from backend.services.memory_service import store_health_observation
from backend.db.postgres import get_db

router = APIRouter()

# ── Per-stage pipeline status (in-process, non-durable) ────────────────────────
# run_full_pipeline is a BackgroundTask: its exceptions are invisible to the
# HTTP caller, and previously ANY stage failing silently killed every later
# stage with no record anywhere. This is a demo-scale substitute for a real
# job table — an in-memory dict capped at the most recent 50 log_ids, evicted
# oldest-first. It resets on restart and is not shared across processes.
_PIPELINE_STATUS: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
_PIPELINE_STATUS_CAP = 50


def _record_stage(log_id: str, stage: str, ok: bool, error: Optional[str], duration_ms: float) -> None:
    entry = _PIPELINE_STATUS.setdefault(log_id, {"log_id": log_id, "stages": {}})
    entry["stages"][stage] = {
        "ok": ok,
        "error": error,
        "duration_ms": round(duration_ms, 1),
    }
    _PIPELINE_STATUS.move_to_end(log_id)
    while len(_PIPELINE_STATUS) > _PIPELINE_STATUS_CAP:
        _PIPELINE_STATUS.popitem(last=False)


async def run_full_pipeline(
    log_id: str,
    user_id: str,
    raw: dict,
    normalized: dict,
    anomalies: Optional[List[dict]] = None,
):
    """
    Runs the 6-stage analysis pipeline as a background task.

    Each stage is isolated: a later stage's failure never blocks an earlier
    stage's already-computed result, and a stage failing while its dependency
    is intact does not stop stages that don't depend on it. Real data
    dependencies are respected — explain/causal/simulation are meaningless
    without a risk_result, so they're skipped (not run on garbage) when
    compute_risk fails.

    `anomalies` is the result COR-1 fixed: detect_anomalies used to run once in
    the route AND once again here for the same log, double-persisting every
    anomaly row. It's computed once, in the route, and passed in.
    """
    print(f"[pipeline] {log_id}: starting")

    if anomalies is None:
        # Only true if some other caller invokes this without the route's
        # precomputed anomalies — still correct, just does the work twice.
        t0 = time.monotonic()
        try:
            anomalies = await detect_anomalies(user_id, log_id, raw)
            _record_stage(log_id, "anomalies", True, None, (time.monotonic() - t0) * 1000)
        except Exception as e:
            print(f"[pipeline] {log_id}: anomalies FAILED: {e}")
            _record_stage(log_id, "anomalies", False, str(e), (time.monotonic() - t0) * 1000)
            anomalies = []

    risk_result = None
    t0 = time.monotonic()
    try:
        risk_result = await compute_risk(user_id, log_id, normalized)
        _record_stage(log_id, "risk", True, None, (time.monotonic() - t0) * 1000)
    except Exception as e:
        print(f"[pipeline] {log_id}: risk FAILED: {e}")
        _record_stage(log_id, "risk", False, str(e), (time.monotonic() - t0) * 1000)

    risk_score = risk_result["risk_score"] if risk_result else None
    risk_category = risk_result.get("risk_category", "Unknown") if risk_result else "Unknown"

    # explain / causal / simulation all read the risk_scores row compute_risk
    # writes — running them without it would explain or simulate nothing real.
    explain_result: Optional[dict] = None
    causal_result: Optional[dict] = None
    if risk_result is not None:
        for stage, coro in (
            ("explain", explain_risk(user_id, log_id, normalized, risk_score)),
            ("causal", run_causal(user_id, log_id, normalized)),
            ("simulation", run_simulation(user_id, log_id, normalized, risk_score)),
        ):
            t0 = time.monotonic()
            try:
                result = await coro
                if stage == "explain":
                    explain_result = result
                elif stage == "causal":
                    causal_result = result
                _record_stage(log_id, stage, True, None, (time.monotonic() - t0) * 1000)
            except Exception as e:
                print(f"[pipeline] {log_id}: {stage} FAILED: {e}")
                _record_stage(log_id, stage, False, str(e), (time.monotonic() - t0) * 1000)
    else:
        for stage in ("explain", "causal", "simulation"):
            _record_stage(log_id, stage, False, "skipped: risk stage did not complete", 0.0)

    # Persist this check-in into vector memory (mem0/pgvector) so it's
    # retrievable context for future chat questions — real-time Garmin data
    # included, since this runs for every source, not just manual entries.
    # Previously wired to nothing: store_health_observation existed but had
    # zero callers anywhere in the app, so mem0's memory store was always
    # empty regardless of how much real health data existed.
    if risk_result is not None:
        t0 = time.monotonic()
        try:
            stored = await store_health_observation(
                user_id,
                health_data=raw,
                risk_score=risk_score,
                risk_category=risk_category,
                shap_contributions=(explain_result or {}).get("shap_contributions", {}),
                causal_chain=(causal_result or {}).get("causal_chain", ""),
                primary_cause=(causal_result or {}).get("primary_cause", ""),
            )
            _record_stage(log_id, "memory", stored, None if stored else "mem0 unavailable", (time.monotonic() - t0) * 1000)
        except Exception as e:
            print(f"[pipeline] {log_id}: memory FAILED: {e}")
            _record_stage(log_id, "memory", False, str(e), (time.monotonic() - t0) * 1000)
    else:
        _record_stage(log_id, "memory", False, "skipped: risk stage did not complete", 0.0)

    agent_result = None
    t0 = time.monotonic()
    try:
        agent_result = await run_cognitive_agent(user_id, log_id)
        _record_stage(log_id, "agent", True, None, (time.monotonic() - t0) * 1000)
    except Exception as e:
        print(f"[pipeline] {log_id}: agent FAILED: {e}")
        _record_stage(log_id, "agent", False, str(e), (time.monotonic() - t0) * 1000)

    # Telegram alerts — best-effort, never blocks or fails the pipeline
    try:
        if risk_category in ("High", "Critical"):
            top_factors = risk_result.get("top_risk_factors", []) if risk_result else []
            recs = agent_result.get("recommendations", []) if agent_result else []
            anomaly_dicts = [
                {"metric": a.get("metric", ""), "message": a.get("message", ""), "severity": a.get("severity", "")}
                for a in (anomalies or [])
            ]
            await send_health_alert(user_id, risk_score, risk_category, top_factors, anomaly_dicts, recs)
        elif anomalies:
            anomaly_dicts = [
                {"metric": a.get("metric", ""), "message": a.get("message", ""), "severity": a.get("severity", "")}
                for a in anomalies
            ]
            await send_anomaly_alert(user_id, anomaly_dicts)
        _record_stage(log_id, "telegram", True, None, 0.0)
    except Exception as e:
        print(f"[pipeline] {log_id}: telegram alert FAILED: {e}")
        _record_stage(log_id, "telegram", False, str(e), 0.0)

    stages = _PIPELINE_STATUS.get(log_id, {}).get("stages", {})
    failed = [s for s, r in stages.items() if not r["ok"]]
    print(f"[pipeline] {log_id}: done. failed stages: {failed or 'none'}")


@router.post("/health-data", response_model=HealthDataResponse)
async def submit_health_data(data: HealthDataInput, background_tasks: BackgroundTasks):
    try:
        result = await ingest(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    # COR-1 fix: this used to run again inside run_full_pipeline for the same
    # log_id, double-persisting every anomaly row (and double-firing Telegram
    # alerts). Computed once here, reused by the background task.
    anomalies = await detect_anomalies(data.user_id, result["log_id"], result["raw"])

    background_tasks.add_task(
        run_full_pipeline,
        result["log_id"],
        data.user_id,
        result["raw"],
        result["normalized"],
        anomalies,
    )

    return HealthDataResponse(
        log_id=result["log_id"],
        status="ingested",
        anomalies_detected=len(anomalies) > 0,
        # True here means "the background task was registered", not "every
        # stage succeeded" — that per-stage truth lives at /pipeline-status.
        pipeline_triggered=True,
        timestamp=result["timestamp"],
    )


@router.get("/health-data/pipeline-status/{log_id}")
async def get_pipeline_status(log_id: str):
    """
    Per-stage outcome of the background pipeline for one check-in.

    In-process and non-durable — see _PIPELINE_STATUS above. A 404 here means
    either the pipeline hasn't started yet, finished so long ago it was
    evicted, or this API process was restarted since the check-in ran.
    """
    entry = _PIPELINE_STATUS.get(log_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No pipeline status recorded for this log_id. It may still be "
                "starting, may predate this API process, or may have been "
                "evicted (only the most recent 50 are kept)."
            ),
        )
    stages = entry["stages"]
    return {
        "log_id": log_id,
        "stages": stages,
        "all_ok": all(s["ok"] for s in stages.values()) if stages else False,
        "complete": "telegram" in stages,  # last stage the pipeline records
    }


@router.get("/health-data/{user_id}")
async def get_latest_health_data(user_id: str):
    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT heart_rate, sleep, steps, stress_level, diet_score, bmi
            FROM health_logs
            WHERE user_id = $1
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            user_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="No health data found")
    return dict(row)


@router.get("/health-data/{user_id}/timeline")
async def get_health_timeline(user_id: str, days: int = 30):
    """
    Read-only, additive endpoint: one row per calendar day (latest submission
    wins) covering every raw field health_logs stores, `extras` included —
    hrv_rmssd, spo2_avg, respiration_avg, body_battery, plus which fields were
    device-measured vs app-defaulted that day. Built for a client that needs
    real per-day history to chart (trends, ranges), not just the single
    latest row `/health-data/{user_id}` returns.

    Does not call Garmin — reads only what's already synced into Postgres, so
    it's safe to poll from a UI without touching login/rate limits. Added
    alongside the existing endpoint rather than extending it, so nothing
    already depending on that response shape is affected.

    Same one-row-per-calendar-day dedup already used for risk/causal/explain
    history reads (DISTINCT ON), so a day with several manual re-submissions
    doesn't count as several days here either.
    """
    days = max(1, min(int(days), 90))
    pool = get_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON ((timestamp AT TIME ZONE 'UTC')::date)
                (timestamp AT TIME ZONE 'UTC')::date AS date,
                timestamp, source, heart_rate, steps, sleep, bmi,
                stress_level, diet_score, systolic_bp, diastolic_bp,
                blood_oxygen, active_minutes, water_intake_ml, extras
            FROM health_logs
            WHERE user_id = $1
            ORDER BY (timestamp AT TIME ZONE 'UTC')::date DESC, timestamp DESC
            LIMIT $2
            """,
            user_id, days,
        )
    days_out = []
    for r in rows:
        d = dict(r)
        d["date"] = d["date"].isoformat()
        d["timestamp"] = d["timestamp"].isoformat()
        extras = d.get("extras")
        if isinstance(extras, str):
            import json
            extras = json.loads(extras) if extras else {}
        d["extras"] = extras or {}
        days_out.append(d)
    # Oldest first — natural chart/reading order
    days_out.reverse()
    return {"user_id": user_id, "days": days_out}
