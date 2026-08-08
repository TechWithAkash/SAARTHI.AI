"""
Air-quality service — environmental CVD advisory (Block C).

THE ONE RULE THAT MATTERS
-------------------------
Nothing in this module may ever reach `composite_risk`, `predict_risk()`, or any
model input. The DarpanEnsemble was never trained on air-quality features, so
folding PM2.5 into the risk score would produce a number that no longer
corresponds to anything the model learned — and that nobody could falsify. Air
quality is displayed BESIDE the CVD score as environmental context, never
blended into it. Every payload carries `not_included_in_risk_score: True` so no
downstream consumer can make that mistake by accident.

PROVENANCE
----------
Every reading is labelled `source`:
  openaq          — fetched live from OpenAQ v3 just now
  cache           — a previous live reading from our DB, with its age reported
  static_fallback — a bundled city baseline, NOT a measurement
OpenAQ v3 requires an API key; without one configured we go straight to the
bundled baselines and say so. A fallback figure is never presented as live.

STANDARDS
---------
AQI conversion uses the Indian National AQI (CPCB) PM2.5 breakpoints, not the
US EPA scale — this is an Indian-context clinical app and CPCB is what Indian
users and clinicians actually read.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from backend.config import settings
from backend.db.postgres import get_db

logger = logging.getLogger(__name__)

# ── CPCB National AQI: PM2.5 sub-index ────────────────────────────────────────
# (conc_low, conc_high, aqi_low, aqi_high, category)
# Source: CPCB National Air Quality Index report (2014), PM2.5 24-hour bands.
CPCB_PM25_BREAKPOINTS = [
    (0.0,   30.0,   0,   50,  "Good"),
    (30.0,  60.0,   51,  100, "Satisfactory"),
    (60.0,  90.0,   101, 200, "Moderate"),
    (90.0,  120.0,  201, 300, "Poor"),
    (120.0, 250.0,  301, 400, "Very Poor"),
    (250.0, 380.0,  401, 500, "Severe"),
]

# WHO 2021 Global Air Quality Guidelines
WHO_ANNUAL_PM25 = 5.0
WHO_24H_PM25 = 15.0

# ── Bundled fallback baselines ────────────────────────────────────────────────
# Approximate recent ANNUAL-MEAN PM2.5 (ug/m3) for major Indian cities, used
# only when no live reading is available. These are order-of-magnitude correct
# for demo purposes and are always labelled `static_fallback` — they are NOT
# measurements and must never be shown as today's air quality.
STATIC_PM25 = {
    "delhi": 100.0, "new delhi": 100.0, "ghaziabad": 105.0, "noida": 95.0,
    "gurugram": 90.0, "kanpur": 85.0, "lucknow": 90.0, "patna": 85.0,
    "jaipur": 65.0, "kolkata": 70.0, "ahmedabad": 65.0, "nagpur": 55.0,
    "mumbai": 45.0, "navi mumbai": 42.0, "thane": 45.0, "pune": 45.0,
    "hyderabad": 40.0, "chennai": 38.0, "bengaluru": 32.0, "bangalore": 32.0,
}
# Used for an unrecognised city: the median of the above rather than a clean
# number, so it is obviously an estimate.
STATIC_DEFAULT_PM25 = 65.0

CACHE_MAX_AGE_MINUTES = 180


def pm25_to_aqi(pm25: float) -> tuple[int, str]:
    """
    Convert PM2.5 (ug/m3) to the Indian National AQI via piecewise-linear
    interpolation within CPCB bands:

        AQI = (AQI_hi - AQI_lo)/(C_hi - C_lo) * (C - C_lo) + AQI_lo

    Concentrations above the top band clamp at 500 (the CPCB scale maximum).
    """
    c = max(0.0, float(pm25))
    for c_lo, c_hi, a_lo, a_hi, label in CPCB_PM25_BREAKPOINTS:
        if c_lo <= c <= c_hi:
            aqi = (a_hi - a_lo) / (c_hi - c_lo) * (c - c_lo) + a_lo
            return int(round(aqi)), label
    return 500, "Severe"


# ── CVD advisory ──────────────────────────────────────────────────────────────
# Long-term PM2.5 exposure is robustly associated with increased cardiovascular
# mortality. Hoek et al., Environ Health 2013;12:43 (systematic review and
# meta-analysis) reported roughly a 11% increase in cardiovascular mortality per
# 10 ug/m3 increment in long-term PM2.5; WHO 2021 Global Air Quality Guidelines
# and successive GBD analyses support the same direction and rough magnitude.
#
# IMPORTANT FRAMING: this is a POPULATION-LEVEL association from long-term
# exposure studies. It is reported here as cited context, with its uncertainty
# stated, and explicitly NOT as this individual's personalised risk change. We
# do not multiply it into anyone's CVD score.
CV_MORTALITY_PCT_PER_10UG = 11.0
CV_MORTALITY_CI = "95% CI approximately 5-16% per 10 ug/m3"
CV_CITATION = (
    "Hoek et al., Environ Health 2013;12:43 (systematic review); "
    "WHO Global Air Quality Guidelines 2021."
)

ADVISORY_BY_CATEGORY = {
    "Good":         "Air quality is not a constraint. Outdoor activity is fine at any time.",
    "Satisfactory": "Outdoor activity is fine. If you are unusually sensitive, prefer mornings.",
    "Moderate":     "Sensitive individuals should ease off prolonged outdoor exertion. Prefer early morning, when particulate levels are typically lowest.",
    "Poor":         "Shift cardio indoors or to early morning. Avoid busy roads; traffic corridors run well above the city average.",
    "Very Poor":    "Avoid outdoor cardio today. Move activity indoors. A well-fitted N95 helps outdoors; a cloth mask does not filter PM2.5.",
    "Severe":       "Do not exercise outdoors. Keep windows shut, run air filtration if available, and minimise time outside. Seek care for chest pain or breathlessness.",
}


def cvd_advisory(pm25: float) -> Dict[str, Any]:
    """
    Environmental cardiovascular advisory for a PM2.5 level.

    Returns cited population-level context plus actionable guidance. Carries
    `not_included_in_risk_score: True` — this is displayed alongside the model's
    CVD score, never folded into it.
    """
    aqi, category = pm25_to_aqi(pm25)
    excess = (pm25 / 10.0) * CV_MORTALITY_PCT_PER_10UG

    return {
        "pm25":                        round(float(pm25), 1),
        "aqi":                         aqi,
        "category":                    category,
        "aqi_standard":                "CPCB National AQI (India), PM2.5 sub-index",
        "who_annual_guideline":        WHO_ANNUAL_PM25,
        "who_24h_guideline":           WHO_24H_PM25,
        "times_who_annual_guideline":  round(pm25 / WHO_ANNUAL_PM25, 1),
        "population_context": (
            f"At {pm25:.0f} ug/m3, this is {pm25 / WHO_ANNUAL_PM25:.1f}x the WHO annual "
            f"guideline of {WHO_ANNUAL_PM25:g} ug/m3. Long-term exposure at this level is "
            f"associated with roughly {excess:.0f}% higher cardiovascular mortality at the "
            f"POPULATION level versus clean air, extrapolated linearly from "
            f"~{CV_MORTALITY_PCT_PER_10UG:g}% per 10 ug/m3."
        ),
        "uncertainty": (
            f"{CV_MORTALITY_CI}. Derived from long-term cohort studies of populations, "
            "not from this individual's data. Linear extrapolation is a simplification; "
            "it is not a prediction of this person's outcome."
        ),
        "citation":                    CV_CITATION,
        "advisory":                    ADVISORY_BY_CATEGORY.get(category, ADVISORY_BY_CATEGORY["Moderate"]),
        "not_included_in_risk_score":  True,
        "disclaimer": (
            "Environmental context only. The DarpanEnsemble was not trained on "
            "air-quality features, so this figure is deliberately excluded from "
            "the CVD risk score and from composite_risk."
        ),
    }


# ── Fetching ──────────────────────────────────────────────────────────────────

async def _fetch_openaq(city: str) -> Optional[Dict[str, Any]]:
    """
    OpenAQ v3 latest PM2.5 for a city. Requires settings.openaq_api_key; v3
    returns 401 without one. Returns None on any failure — callers fall back.
    """
    if not settings.openaq_api_key:
        return None

    headers = {"X-API-Key": settings.openaq_api_key}
    try:
        # Explicit timeout: a hung request must never stall a demo.
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0)) as client:
            loc = await client.get(
                "https://api.openaq.org/v3/locations",
                params={"limit": 25, "parameters_id": 2},  # 2 = pm25
                headers=headers,
            )
            if loc.status_code != 200:
                logger.warning(f"[air_quality] OpenAQ locations HTTP {loc.status_code}")
                return None

            wanted = city.strip().lower()
            match = None
            for item in (loc.json().get("results") or []):
                blob = f"{item.get('name','')} {item.get('locality','')}".lower()
                if wanted and wanted in blob:
                    match = item
                    break
            if match is None:
                return None

            for sensor in (match.get("sensors") or []):
                if (sensor.get("parameter") or {}).get("name") != "pm25":
                    continue
                meas = await client.get(
                    f"https://api.openaq.org/v3/sensors/{sensor['id']}",
                    headers=headers,
                )
                if meas.status_code != 200:
                    continue
                results = meas.json().get("results") or []
                if not results:
                    continue
                value = ((results[0].get("latest") or {}).get("value"))
                if value is None:
                    continue
                return {
                    "pm25": float(value),
                    "city": match.get("name") or city,
                    "payload": {"location_id": match.get("id"), "sensor_id": sensor["id"]},
                }
    except Exception as e:
        logger.warning(f"[air_quality] OpenAQ fetch failed: {e}")
    return None


async def _read_cache(city: str) -> Optional[Dict[str, Any]]:
    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT pm25, aqi, category, fetched_at,
                   EXTRACT(EPOCH FROM (NOW() - fetched_at)) / 60 AS age_minutes
            FROM air_quality_readings
            WHERE lower(city) = lower($1) AND source = 'openaq'
            ORDER BY fetched_at DESC LIMIT 1
            """,
            city,
        )
    if row and row["age_minutes"] is not None and row["age_minutes"] <= CACHE_MAX_AGE_MINUTES:
        return {"pm25": float(row["pm25"]), "age_minutes": round(float(row["age_minutes"]), 1)}
    return None


async def _persist(user_id: Optional[str], city: str, reading: Dict[str, Any], source: str) -> None:
    pool = get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO air_quality_readings
                (user_id, city, pm25, aqi, category, source, payload, fetched_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            user_id, city, reading["pm25"], reading["aqi"], reading["category"],
            source, json.dumps(reading.get("payload") or {}),
            datetime.now(timezone.utc),
        )


async def get_air_quality(
    city: Optional[str] = None,
    user_id: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Resolves air quality for a city: recent cache -> live OpenAQ -> bundled
    baseline. Never raises on network failure; always labels its `source`.
    """
    city = (city or settings.default_city or "Mumbai").strip()

    # 1. Recent cached live reading
    if not force_refresh:
        try:
            cached = await _read_cache(city)
            if cached:
                out = cvd_advisory(cached["pm25"])
                return {
                    **out, "city": city, "source": "cache",
                    "cache_age_minutes": cached["age_minutes"],
                    "is_live_measurement": True,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            logger.warning(f"[air_quality] cache lookup failed: {e}")

    # 2. Live OpenAQ
    live = await _fetch_openaq(city)
    if live:
        out = cvd_advisory(live["pm25"])
        try:
            await _persist(user_id, live["city"], {**out, "payload": live["payload"]}, "openaq")
        except Exception as e:
            logger.warning(f"[air_quality] persist failed: {e}")
        return {
            **out, "city": live["city"], "source": "openaq",
            "is_live_measurement": True,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    # 3. Bundled baseline — explicitly NOT a measurement
    key = city.lower()
    known = key in STATIC_PM25
    pm25 = STATIC_PM25.get(key, STATIC_DEFAULT_PM25)
    out = cvd_advisory(pm25)
    return {
        **out,
        "city": city,
        "source": "static_fallback",
        "is_live_measurement": False,
        "city_recognised": known,
        "fallback_reason": (
            "OPENAQ_API_KEY is not configured"
            if not settings.openaq_api_key
            else "no live OpenAQ reading available for this city"
        ),
        "fallback_note": (
            "Approximate recent ANNUAL-MEAN PM2.5 for this city, not today's "
            "measurement. Shown so the advisory still works offline."
            + ("" if known else " City not in the bundled set; using a national mid-range estimate.")
        ),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


async def cvd_context(user_id: str, city: Optional[str] = None) -> Dict[str, Any]:
    """
    The user's model-derived CVD score and the environmental advisory, side by
    side as two separate numbers. Deliberately does not combine them.
    """
    air = await get_air_quality(city=city, user_id=user_id)

    pool = get_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT shap_contributions, risk_score, timestamp
            FROM risk_scores WHERE user_id = $1
            ORDER BY timestamp DESC LIMIT 1
            """,
            user_id,
        )

    cvd = None
    if row and row["shap_contributions"]:
        blob = row["shap_contributions"]
        if isinstance(blob, str):
            try:
                blob = json.loads(blob)
            except (TypeError, ValueError):
                blob = {}
        if isinstance(blob, dict):
            cvd = blob.get("cvd_risk")

    return {
        "user_id": user_id,
        "cardiovascular_risk": {
            "value":  cvd,
            "source": "DarpanEnsemble v2 (Transformer + XGBoost + Ridge meta)",
            "basis":  "the user's 12 clinical and lifestyle features",
            "as_of":  row["timestamp"].isoformat() if row and row["timestamp"] else None,
        },
        "environmental_advisory": air,
        "relationship": (
            "These are two independent figures. The CVD score is model-derived "
            "from this user's own data; the air-quality figure is environmental "
            "context from published population-level epidemiology. They are "
            "shown side by side and are NOT combined — the model was never "
            "trained on air-quality features."
        ),
        "combined": False,
    }
