-- DarpanAI PostgreSQL Schema
-- Run once on startup (CREATE TABLE IF NOT EXISTS = idempotent)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Users
CREATE TABLE IF NOT EXISTS users (
    user_id      TEXT PRIMARY KEY,
    age          INT,
    gender       TEXT,
    health_goals JSONB DEFAULT '[]',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Health logs (flattened from MongoDB nested structure)
CREATE TABLE IF NOT EXISTS health_logs (
    log_id           TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL,
    heart_rate       FLOAT,
    steps            FLOAT,
    sleep            FLOAT,
    bmi              FLOAT,
    stress_level     FLOAT,
    diet_score       FLOAT,
    systolic_bp      FLOAT,
    diastolic_bp     FLOAT,
    blood_oxygen     FLOAT,
    active_minutes   FLOAT,
    water_intake_ml  FLOAT,
    source           TEXT DEFAULT 'manual',
    -- normalized [0,1] versions
    heart_rate_norm  FLOAT,
    steps_norm       FLOAT,
    sleep_norm       FLOAT,
    bmi_norm         FLOAT,
    stress_level_norm FLOAT,
    diet_score_norm  FLOAT,
    timestamp        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_health_logs_user_id   ON health_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_health_logs_timestamp ON health_logs(timestamp DESC);

-- Risk scores
CREATE TABLE IF NOT EXISTS risk_scores (
    id                  SERIAL PRIMARY KEY,
    user_id             TEXT NOT NULL,
    log_id              TEXT,
    risk_score          FLOAT,
    risk_category       TEXT,
    top_risk_factors    JSONB DEFAULT '[]',
    shap_contributions  JSONB DEFAULT '{}',
    primary_cause       TEXT DEFAULT '',
    causal_chain        TEXT DEFAULT '',
    model_version       TEXT,
    raw_features        JSONB DEFAULT '{}',
    timestamp           TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_risk_scores_user_id   ON risk_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_risk_scores_timestamp ON risk_scores(timestamp DESC);

-- Simulations
CREATE TABLE IF NOT EXISTS simulations (
    id                      SERIAL PRIMARY KEY,
    user_id                 TEXT NOT NULL,
    based_on_log_id         TEXT,
    scenarios               JSONB DEFAULT '{}',
    timeline_days           JSONB DEFAULT '[]',
    projected_risk_reduction JSONB DEFAULT '{}',
    scenario_assumptions    JSONB DEFAULT '{}',
    generated_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_simulations_user_id ON simulations(user_id);

-- Causal results
CREATE TABLE IF NOT EXISTS causal_results (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    ranked_factors  JSONB DEFAULT '[]',
    primary_cause   TEXT DEFAULT '',
    causal_chain    TEXT DEFAULT '',
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_causal_results_user_id ON causal_results(user_id);

-- Recommendations
CREATE TABLE IF NOT EXISTS recommendations (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    log_id          TEXT,
    method          TEXT,
    risk_score      FLOAT,
    recommendations JSONB DEFAULT '[]',
    agent_metadata  JSONB DEFAULT '{}',
    generated_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON recommendations(user_id);
-- Safe migration for existing installs
ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS agent_metadata JSONB DEFAULT '{}';

-- Clinical profile columns for DarpanEnsemble 12-feature model
ALTER TABLE users ADD COLUMN IF NOT EXISTS whr              FLOAT DEFAULT 0.85;
ALTER TABLE users ADD COLUMN IF NOT EXISTS fam_diabetes     SMALLINT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS fam_cvd          SMALLINT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS fam_hypertension SMALLINT DEFAULT 0;


-- Anomalies
CREATE TABLE IF NOT EXISTS anomalies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         TEXT NOT NULL,
    log_id          TEXT,
    metric          TEXT,
    observed_value  FLOAT,
    expected_range  JSONB DEFAULT '{}',
    deviation_pct   FLOAT,
    z_score         FLOAT,
    severity        TEXT,
    layer           TEXT,
    message         TEXT,
    acknowledged    BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    detected_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_anomalies_user_id    ON anomalies(user_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at ON anomalies(detected_at DESC);

-- Explanations
CREATE TABLE IF NOT EXISTS explanations (
    id                  SERIAL PRIMARY KEY,
    user_id             TEXT NOT NULL,
    log_id              TEXT,
    risk_score          FLOAT,
    base_value          FLOAT,
    shap_contributions  JSONB DEFAULT '{}',
    risk_drivers        JSONB DEFAULT '[]',
    protective_factors  JSONB DEFAULT '[]',
    descriptions        JSONB DEFAULT '{}',
    primary_driver      TEXT DEFAULT '',
    timestamp           TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_explanations_user_id ON explanations(user_id);

-- Telegram connections
-- chat_id is BIGINT: Telegram chat IDs exceed int32 range.
CREATE TABLE IF NOT EXISTS telegram_connections (
    user_id     TEXT PRIMARY KEY,
    link_token  TEXT,
    chat_id     BIGINT,
    username    TEXT,
    linked      BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    linked_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_telegram_link_token ON telegram_connections(link_token);
CREATE INDEX IF NOT EXISTS idx_telegram_chat_id    ON telegram_connections(chat_id);

-- ── Wearable ingestion (BP-6) ────────────────────────────────────────────────
-- Device-measured metrics that don't warrant their own column yet: real
-- hrv_rmssd (replaces the HC-03 proxy), body battery, resting HR, spo2,
-- respiration, and the raw Garmin payload for audit. JSONB rather than a wide
-- migration so new device fields don't need a schema change each time.
ALTER TABLE health_logs ADD COLUMN IF NOT EXISTS extras JSONB DEFAULT '{}';

-- Supports the Garmin backfill's per-day dedup query. Deliberately NOT UNIQUE:
-- this file is re-executed on every startup (postgres.py), and a UNIQUE index
-- that existing rows already violate would abort boot. Dedup is enforced in
-- garmin_service._upsert_day() instead, which deletes the day before inserting.
CREATE INDEX IF NOT EXISTS idx_health_logs_user_source_ts
    ON health_logs (user_id, source, timestamp DESC);

-- Air-quality snapshots (Block C). Cached so a venue network failure or an
-- OpenAQ outage can't break the CVD advisory during a demo.
CREATE TABLE IF NOT EXISTS air_quality_readings (
    id          SERIAL PRIMARY KEY,
    user_id     TEXT,
    city        TEXT,
    pm25        FLOAT,
    aqi         INT,
    category    TEXT,
    source      TEXT,            -- 'openaq' | 'static_fallback' | 'cache'
    payload     JSONB DEFAULT '{}',
    fetched_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_air_quality_user ON air_quality_readings(user_id, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_air_quality_city ON air_quality_readings(city, fetched_at DESC);

-- Garmin credentials are NEVER stored here — they live in .env only. This
-- table records sync state so the UI can show provenance and last-sync age.
CREATE TABLE IF NOT EXISTS wearable_sync_state (
    user_id       TEXT PRIMARY KEY,
    provider      TEXT DEFAULT 'garmin',
    display_name  TEXT,
    last_synced_at TIMESTAMPTZ,
    days_synced   INT DEFAULT 0,
    last_status   TEXT,
    last_error    TEXT
);
