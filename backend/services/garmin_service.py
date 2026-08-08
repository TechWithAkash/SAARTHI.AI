"""
Garmin Connect adapter — real wearable telemetry (BP-6).

WHY THIS EXISTS
---------------
The Apple HealthKit path needs a provisioned Apple Developer account we don't
have access to. Garmin Connect works entirely server-side with an account
login, so it needs no mobile provisioning at all. It is the difference between
demoing on hand-typed numbers and demoing on a real body.

WHAT IT UNLOCKS
---------------
  * REAL hrv_rmssd, replacing the derive_hrv() proxy (HC-03). This is the big
    one — HRV is a genuine input to the 12-feature ensemble, and until now it
    was a made-up function of resting heart rate.
  * REAL multi-day history, replacing the [day]*30 tiling (HC-05), which is
    what makes the transformer's temporal layers and XGBoost's std/trend
    features mean anything at all.

OPERATIONAL SAFETY — read before touching login code
----------------------------------------------------
garminconnect is a reverse-engineered client against a private API. Garmin
temporarily blocks an IP after repeated failed logins, so:
  * We stop permanently after settings.garmin_max_login_attempts (default 2).
  * We try CACHED TOKENS FIRST and only hit SSO when they're absent or stale.
  * We refuse to attempt login at all unless settings.garmin_configured is
    True, which screens out the placeholder credentials from the setup docs.
  * Every raw response is cached to disk, and any live failure falls back to
    that cache. On stage, a third-party login must never be a single point of
    failure.

Credentials come from .env only. They are never written to the database, never
logged, and never returned by any endpoint.
"""

import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.db.postgres import get_db

logger = logging.getLogger(__name__)

CACHE_DIR = Path(settings.garmin_token_store).parent / ".garmin_cache"

# App-level neutral defaults, used when Garmin genuinely has no value for a
# required field. Every substitution is recorded in extras["defaulted_fields"]
# so "which of these numbers are real?" is an answerable question.
APP_DEFAULTS = {
    "heart_rate":   72.0,
    "steps":        0.0,
    "sleep":        7.0,
    "bmi":          23.5,
    "stress_level": 4.0,
    "diet_score":   6.0,   # Garmin has NO food log via this API — always defaulted
}

# Fields Garmin cannot supply at all. Stated explicitly so nobody later
# mistakes a default for a measurement.
UNAVAILABLE_FROM_GARMIN = ("diet_score",)

_client = None
_login_attempts = 0
_login_blocked = False


# ── Defensive extraction ──────────────────────────────────────────────────────
# Garmin's JSON keys vary by device, firmware and endpoint, and missing metrics
# simply omit their key. Every read goes through these so a shape change
# degrades to None instead of raising mid-sync.

def _dig(payload: Any, path: str) -> Any:
    """
    Walk a dotted path through nested dicts and lists, returning None on any
    miss. A numeric segment indexes a list, so "dateWeightList.0.bmi" works —
    Garmin wraps several metrics (weight, body composition, HRV readings) in
    single-element arrays.
    """
    cur = payload
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, (list, tuple)):
            if not part.lstrip("-").isdigit():
                return None
            idx = int(part)
            if not (-len(cur) <= idx < len(cur)):
                return None
            cur = cur[idx]
        else:
            return None
        if cur is None:
            return None
    return cur


def _first(payload: Any, *paths: str) -> Any:
    """First non-None value among several candidate dotted paths."""
    for p in paths:
        val = _dig(payload, p)
        if val is not None:
            return val
    return None


def _num(val: Any) -> Optional[float]:
    if val is None or isinstance(val, bool):
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # reject NaN


def garmin_stress_to_app_scale(garmin_stress: Optional[float]) -> Optional[float]:
    """
    Garmin reports stress on 0-100; the app's models expect stress_level 1-10.

    Linear map: 0 -> 1.0, 100 -> 10.0, i.e. 1 + (g/100)*9.
    Linear (not a curve) because the ensemble was trained on a 1-10 scale whose
    own distribution we can't reshape after the fact — introducing a nonlinear
    remap here would silently shift every stress-driven prediction.
    Garmin uses -1/-2 sentinels for "no data"; those return None.
    """
    g = _num(garmin_stress)
    if g is None or g < 0:
        return None
    return round(max(1.0, min(10.0, 1.0 + (g / 100.0) * 9.0)), 2)


def _extract_steps(stats: Any, daily_row: Any = None) -> Optional[float]:
    return _num(_first(daily_row or {}, "totalSteps", "steps")) or _num(
        _first(stats or {}, "totalSteps", "steps", "dailyStepCount")
    )


def _extract_resting_hr(stats: Any, rhr: Any = None) -> Optional[float]:
    return _num(_first(
        stats or {},
        "restingHeartRate", "restingHeartRateTimestamp.value",
        "minHeartRate", "averageHeartRate",
    )) or _num(_first(
        rhr or {},
        "restingHeartRate",
        "allMetrics.metricsMap.WELLNESS_RESTING_HEART_RATE.0.value",
    ))


def _extract_sleep_hours(sleep: Any, stats: Any = None) -> Optional[float]:
    secs = _num(_first(
        sleep or {},
        "dailySleepDTO.sleepTimeSeconds",
        "sleepTimeSeconds",
        "dailySleepDTO.napTimeSeconds",
    ))
    if secs is None:
        secs = _num(_first(stats or {}, "sleepingSeconds", "measurableAsleepDuration"))
    if secs is None:
        return None
    hours = secs / 3600.0
    # Guard against sentinel/garbage values outside any plausible night
    return round(hours, 2) if 0 < hours <= 24 else None


def _extract_hrv_rmssd(hrv: Any) -> Optional[float]:
    """
    The real prize: measured RMSSD in ms, which replaces derive_hrv().
    lastNightAvg is Garmin's overnight RMSSD average.
    """
    v = _num(_first(
        hrv or {},
        "hrvSummary.lastNightAvg", "hrvSummary.weeklyAvg",
        "hrvSummary.lastNight5MinHigh", "lastNightAvg",
    ))
    # Physiologically plausible RMSSD band; outside it, treat as no reading
    return v if (v is not None and 1 <= v <= 300) else None


def _extract_stress(stress: Any, stats: Any = None) -> Optional[float]:
    raw = _first(
        stress or {}, "avgStressLevel", "averageStressLevel", "overallStressLevel",
    )
    if raw is None:
        raw = _first(stats or {}, "averageStressLevel", "avgStressLevel", "stressQualifier")
    return garmin_stress_to_app_scale(raw)


def _extract_bmi(body: Any) -> tuple[Optional[float], Optional[float]]:
    """Returns (bmi, weight_kg). Garmin reports weight in GRAMS."""
    bmi = _num(_first(
        body or {}, "bmi",
        "dateWeightList.0.bmi", "totalAverage.bmi",
    ))
    grams = _num(_first(
        body or {}, "weight",
        "dateWeightList.0.weight", "totalAverage.weight",
    ))
    kg = round(grams / 1000.0, 1) if grams and grams > 1000 else _num(grams)
    return (bmi if (bmi and 10 <= bmi <= 70) else None), kg


def _extract_spo2(spo2: Any) -> Optional[float]:
    v = _num(_first(spo2 or {}, "averageSpO2", "avgSleepSpO2", "latestSpO2"))
    return v if (v is not None and 50 <= v <= 100) else None


def _extract_body_battery(row: Any) -> Dict[str, Optional[float]]:
    return {
        "body_battery_charged": _num(_first(row or {}, "charged", "bodyBatteryChargedValue")),
        "body_battery_drained": _num(_first(row or {}, "drained", "bodyBatteryDrainedValue")),
    }


# ── Disk cache ────────────────────────────────────────────────────────────────

def _cache_path(endpoint: str, key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in f"{endpoint}_{key}")
    return CACHE_DIR / f"{safe}.json"


def _cache_write(endpoint: str, key: str, payload: Any) -> None:
    try:
        _cache_path(endpoint, key).write_text(json.dumps(payload, default=str))
    except Exception as e:
        logger.warning(f"[garmin] cache write failed for {endpoint}/{key}: {e}")


def _cache_read(endpoint: str, key: str) -> Any:
    try:
        p = _cache_path(endpoint, key)
        if p.exists():
            return json.loads(p.read_text())
    except Exception as e:
        logger.warning(f"[garmin] cache read failed for {endpoint}/{key}: {e}")
    return None


# ── Login ─────────────────────────────────────────────────────────────────────

class GarminUnavailable(RuntimeError):
    """Raised when we cannot and must not reach Garmin. Callers fall back to cache."""


def tokens_cached() -> bool:
    return Path(settings.garmin_token_store).exists()


def _login_sync():
    """
    Blocking login. Cached tokens first, SSO only as a fallback, hard-capped
    attempt count. Never called unless settings.garmin_configured.
    """
    global _client, _login_attempts, _login_blocked

    if _client is not None:
        return _client
    if _login_blocked:
        raise GarminUnavailable(
            "Garmin login disabled for this process after "
            f"{_login_attempts} failed attempt(s). Restart the API to retry — "
            "repeated attempts get the IP temporarily blocked."
        )

    import garminconnect

    store = settings.garmin_token_store

    # 1. Resume from cached tokens — no SSO round-trip, no attempt consumed.
    if Path(store).exists():
        try:
            c = garminconnect.Garmin()
            c.login(store)
            _client = c
            logger.info("[garmin] resumed from cached tokens (no SSO)")
            return _client
        except Exception as e:
            logger.warning(f"[garmin] cached tokens stale ({type(e).__name__}); trying SSO")

    if not settings.garmin_configured:
        raise GarminUnavailable(
            "GARMIN_EMAIL / GARMIN_PASSWORD are unset or still the placeholder "
            "values from the setup docs. Refusing to attempt login."
        )

    if _login_attempts >= settings.garmin_max_login_attempts:
        _login_blocked = True
        raise GarminUnavailable("Login attempt cap reached.")

    _login_attempts += 1
    try:
        def _no_interactive_mfa() -> str:
            # A web request cannot block on stdin. Surface a clear instruction
            # instead of hanging a worker thread forever.
            raise GarminUnavailable(
                "Garmin is requesting an MFA code, which cannot be entered from "
                "an API request. Run the probe script interactively once to mint "
                f"and cache tokens at {store}, then retry."
            )

        c = garminconnect.Garmin(
            email=settings.garmin_email,
            password=settings.garmin_password,
            prompt_mfa=_no_interactive_mfa,
        )
        c.login()
        try:
            # garminconnect 0.3.2 has no `.garth` attribute (older versions of
            # this library wrapped the `garth` package directly; 0.3.2 vendors
            # its own client instead). Token persistence lives on `.client`
            # (a garminconnect.client.Client), not on a `.garth` attribute
            # that doesn't exist on this version — confirmed via
            # `hasattr(Garmin(...), 'garth')` returning False. Calling the
            # wrong attribute here would have raised AttributeError right
            # after a successful login, burning a real login attempt while
            # silently failing to cache anything.
            c.client.dump(store)
            logger.info(f"[garmin] tokens cached to {store}")
        except Exception as e:
            logger.warning(f"[garmin] could not cache tokens: {e}")
        _client = c
        return _client
    except GarminUnavailable:
        raise
    except Exception as e:
        if _login_attempts >= settings.garmin_max_login_attempts:
            _login_blocked = True
        # Deliberately does not include the password or the exception repr of
        # any request body.
        raise GarminUnavailable(
            f"Garmin login failed ({type(e).__name__}). Attempt "
            f"{_login_attempts}/{settings.garmin_max_login_attempts}."
        ) from None


async def _api(endpoint: str, key: str, fn) -> tuple[Any, str]:
    """
    Calls a Garmin endpoint in a worker thread, caching the result.
    Returns (payload, provenance) where provenance is 'live' or 'cache'.
    Never raises on upstream failure if a cached copy exists.
    """
    try:
        client = await asyncio.to_thread(_login_sync)
        payload = await asyncio.to_thread(fn, client)
        if payload is not None:
            _cache_write(endpoint, key, payload)
            return payload, "live"
    except Exception as e:
        logger.warning(f"[garmin] {endpoint}({key}) failed: {e}")

    cached = _cache_read(endpoint, key)
    if cached is not None:
        logger.info(f"[garmin] serving {endpoint}({key}) from disk cache")
        return cached, "cache"
    return None, "unavailable"


# ── Public fetch API ──────────────────────────────────────────────────────────

async def fetch_core(cdate: str) -> Dict[str, Any]:
    """
    The 6 fields HealthDataInput requires, plus which ones are real.
    None means Garmin had no value — the caller substitutes an app default.
    """
    stats, p1 = await _api("stats", cdate, lambda c: c.get_stats(cdate))
    sleep, p2 = await _api("sleep", cdate, lambda c: c.get_sleep_data(cdate))
    stress, p3 = await _api("stress", cdate, lambda c: c.get_stress_data(cdate))
    body, p4 = await _api("body", cdate, lambda c: c.get_body_composition(cdate, cdate))

    bmi, weight_kg = _extract_bmi(body)
    core = {
        "heart_rate":   _extract_resting_hr(stats),
        "steps":        _extract_steps(stats),
        "sleep":        _extract_sleep_hours(sleep, stats),
        "bmi":          bmi,
        "stress_level": _extract_stress(stress, stats),
        "diet_score":   None,   # Garmin has no food log via this API
    }
    return {
        "date":       cdate,
        "core":       core,
        "weight_kg":  weight_kg,
        "provenance": "cache" if "cache" in (p1, p2, p3, p4) else ("live" if p1 == "live" else "unavailable"),
        "measured":   [k for k, v in core.items() if v is not None],
    }


async def fetch_enhancements(cdate: str) -> Dict[str, Any]:
    """
    Device metrics that go into health_logs.extras. hrv_rmssd is the one that
    actually changes a prediction — it overrides the HC-03 proxy.
    """
    hrv, _   = await _api("hrv",   cdate, lambda c: c.get_hrv_data(cdate))
    spo2, _  = await _api("spo2",  cdate, lambda c: c.get_spo2_data(cdate))
    resp, _  = await _api("resp",  cdate, lambda c: c.get_respiration_data(cdate))

    extras: Dict[str, Any] = {}
    rmssd = _extract_hrv_rmssd(hrv)
    if rmssd is not None:
        extras["hrv_rmssd"] = rmssd
    sp = _extract_spo2(spo2)
    if sp is not None:
        extras["spo2_avg"] = sp
    rr = _num(_first(resp or {}, "avgWakingRespirationValue", "avgSleepRespirationValue"))
    if rr is not None:
        extras["respiration_avg"] = rr
    return extras


async def fetch_ranges(start: str, end: str) -> Dict[str, Dict[str, Any]]:
    """
    Range endpoints: 2 HTTP calls cover the whole backfill window instead of
    one per day. Returns {calendar_date: {...}} for cheap per-day lookup.
    """
    steps_list, _ = await _api("daily_steps", f"{start}_{end}",
                               lambda c: c.get_daily_steps(start, end))
    bb_list, _ = await _api("body_battery", f"{start}_{end}",
                            lambda c: c.get_body_battery(start, end))

    by_date: Dict[str, Dict[str, Any]] = {}
    for row in (steps_list or []):
        d = _first(row, "calendarDate", "date", "statisticsStartDate")
        if d:
            by_date.setdefault(str(d)[:10], {})["steps_row"] = row
    for row in (bb_list or []):
        d = _first(row, "date", "calendarDate")
        if d:
            by_date.setdefault(str(d)[:10], {})["bb_row"] = row
    return by_date


# ── Ingestion ─────────────────────────────────────────────────────────────────

async def _upsert_day(user_id: str, cdate: str, core: Dict[str, Any], extras: Dict[str, Any]) -> str:
    """
    Writes one Garmin day, replacing any prior Garmin row for the same calendar
    date so a re-run is idempotent. Reuses ingestion_service.ingest() so
    normalization stays identical to the manual path.

    Dedup is done here rather than with a UNIQUE index because schema.sql is
    re-executed on every startup and a unique index that existing rows already
    violated would abort boot.
    """
    from backend.models.health import HealthDataInput
    from backend.services.ingestion_service import ingest

    defaulted = [k for k, v in core.items() if v is None]
    filled = {k: (core.get(k) if core.get(k) is not None else APP_DEFAULTS[k]) for k in APP_DEFAULTS}

    # asyncpg's ::date cast requires an actual datetime.date object for its
    # binary DATE codec — passing the ISO string directly raises
    # `AttributeError: 'str' object has no attribute 'toordinal'` deep inside
    # the driver. Both queries below bind this once-converted value instead
    # of the raw cdate string. Found by testing this function directly
    # against real cached Garmin responses — every single backfilled day
    # failed here, even though extraction itself was correct.
    cdate_obj = date.fromisoformat(cdate)

    pool = get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM health_logs
            WHERE user_id = $1 AND source = 'garmin'
              AND (timestamp AT TIME ZONE 'UTC')::date = $2::date
            """,
            user_id, cdate_obj,
        )

    payload = HealthDataInput(
        user_id=user_id,
        source="garmin",
        heart_rate=filled["heart_rate"],
        steps=filled["steps"],
        sleep=filled["sleep"],
        bmi=filled["bmi"],
        stress_level=filled["stress_level"],
        diet_score=filled["diet_score"],
        hrv_rmssd=extras.get("hrv_rmssd"),
        extras={
            **extras,
            "garmin_date":      cdate,
            "defaulted_fields": defaulted,
            "measured_fields":  [k for k, v in core.items() if v is not None],
        },
    )
    result = await ingest(payload)

    # Stamp the row to the day it describes, not to "now", or a 14-day backfill
    # collapses into a single timestamp and the sequence builder sees no history.
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE health_logs SET timestamp = $1::date + interval '12 hours' WHERE log_id = $2",
            cdate_obj, result["log_id"],
        )
    return result["log_id"]


async def backfill(user_id: str, days: int = 14) -> Dict[str, Any]:
    """
    Pulls `days` of history and writes one health_logs row per day.

    Range endpoints supply steps and body battery in 2 calls; the per-day
    endpoints (sleep, HRV, stress) still need one call each, so this is
    O(days) requests overall — kept modest and sequential to avoid tripping
    rate limits on a private API.
    """
    days = max(1, min(int(days), 90))
    today = date.today()
    start = (today - timedelta(days=days - 1)).isoformat()
    end = today.isoformat()

    ranges = await fetch_ranges(start, end)

    ingested, failed, provenance = [], [], set()
    for offset in range(days):
        cdate = (today - timedelta(days=offset)).isoformat()
        try:
            core_res = await fetch_core(cdate)
            core = core_res["core"]
            provenance.add(core_res["provenance"])

            # Range data fills gaps the per-day endpoint missed
            row = ranges.get(cdate, {})
            if core["steps"] is None:
                core["steps"] = _extract_steps(None, row.get("steps_row"))

            extras = await fetch_enhancements(cdate)
            extras.update({k: v for k, v in _extract_body_battery(row.get("bb_row")).items() if v is not None})
            if core_res.get("weight_kg"):
                extras["weight_kg"] = core_res["weight_kg"]

            # A day with nothing measured is a gap, not a reading — skip it
            # rather than writing a row of pure defaults.
            if not core_res["measured"] and not extras:
                failed.append({"date": cdate, "reason": "no data for this date"})
                continue

            await _upsert_day(user_id, cdate, core, extras)
            ingested.append({
                "date": cdate,
                "measured": core_res["measured"],
                "defaulted": [k for k, v in core.items() if v is None],
                "hrv_rmssd": extras.get("hrv_rmssd"),
            })
        except Exception as e:
            logger.warning(f"[garmin] backfill failed for {cdate}: {e}")
            failed.append({"date": cdate, "reason": f"{type(e).__name__}: {e}"})

    status = "ok" if ingested else "failed"
    source = "cache" if provenance == {"cache"} else ("live" if "live" in provenance else "unavailable")
    await _record_sync(user_id, status, len(ingested),
                       None if ingested else "no days ingested")

    return {
        "user_id":       user_id,
        "status":        status,
        "source":        source,
        "days_requested": days,
        "days_ingested": len(ingested),
        "date_range":    {"start": start, "end": end},
        "ingested":      ingested,
        "failed":        failed,
        "unavailable_from_garmin": list(UNAVAILABLE_FROM_GARMIN),
        "note": (
            "diet_score has no Garmin source and is always the app default "
            f"({APP_DEFAULTS['diet_score']}); see defaulted_fields per row."
        ),
    }


async def _record_sync(user_id: str, status: str, days: int, error: Optional[str]) -> None:
    """Persists sync state. Never stores credentials."""
    name = None
    try:
        if _client is not None:
            name = await asyncio.to_thread(_client.get_full_name)
    except Exception:
        pass

    pool = get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO wearable_sync_state
                (user_id, provider, display_name, last_synced_at, days_synced, last_status, last_error)
            VALUES ($1, 'garmin', $2, $3, $4, $5, $6)
            ON CONFLICT (user_id) DO UPDATE SET
                display_name = COALESCE(EXCLUDED.display_name, wearable_sync_state.display_name),
                last_synced_at = EXCLUDED.last_synced_at,
                days_synced = EXCLUDED.days_synced,
                last_status = EXCLUDED.last_status,
                last_error = EXCLUDED.last_error
            """,
            user_id, name, datetime.now(timezone.utc), days, status, error,
        )


async def status(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Connection + sync status. Safe to call when nothing is configured — that is
    the normal demo path. Never returns credentials.
    """
    out: Dict[str, Any] = {
        "provider":          "garmin",
        "configured":        settings.garmin_configured,
        "tokens_cached":     tokens_cached(),
        "login_blocked":     _login_blocked,
        "login_attempts":    _login_attempts,
        "max_login_attempts": settings.garmin_max_login_attempts,
        "cache_dir":         str(CACHE_DIR),
        "cached_responses":  len(list(CACHE_DIR.glob("*.json"))) if CACHE_DIR.exists() else 0,
        "unavailable_from_garmin": list(UNAVAILABLE_FROM_GARMIN),
    }
    if not settings.garmin_configured:
        out["hint"] = (
            "Set real GARMIN_EMAIL and GARMIN_PASSWORD in .env. The values "
            "currently present are unset or the setup-doc placeholders, so no "
            "login will be attempted."
        )

    if user_id:
        pool = get_db()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT display_name, last_synced_at, days_synced, last_status, last_error "
                "FROM wearable_sync_state WHERE user_id = $1",
                user_id,
            )
            n = await conn.fetchval(
                "SELECT COUNT(*) FROM health_logs WHERE user_id = $1 AND source = 'garmin'",
                user_id,
            )
        out["last_sync"] = dict(row) if row else None
        out["garmin_rows_in_db"] = int(n or 0)
    return out
