from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/darpanai_db"
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    redis_url: str = "redis://localhost:6379"
    # NOTE: the retired 7-feature ml/risk_model.pkl is no longer loaded by any
    # service. Model paths now live in ensemble_service.MODEL_DIR.
    telegram_bot_token: str = ""
    hf_token: str = ""

    # ── Garmin Connect (BP-6) ────────────────────────────────────────────────
    # Credentials come from .env ONLY and are never persisted to the database,
    # logged, or returned by any endpoint. garmin_token_store caches the OAuth
    # tokens garth negotiates, so a normal run does not re-hit Garmin SSO.
    garmin_email: str = ""
    garmin_password: str = ""
    garmin_token_store: str = ".garmin_tokens"
    # Garmin temporarily blocks an IP after repeated failed logins, so the
    # adapter stops after this many attempts and stays stopped for the process
    # lifetime. Do not raise this on a venue network.
    garmin_max_login_attempts: int = 2

    # ── Air quality (Block C) ────────────────────────────────────────────────
    # OpenAQ v3 requires an API key. Without one the service falls back to
    # bundled city data and labels the reading `static_fallback` — it never
    # presents fallback numbers as live measurements.
    openaq_api_key: str = ""
    default_city: str = "Mumbai"

    # ── Clinical guideline RAG (rag.py, reused unmodified) ──────────────────
    # Directory of .md clinical guideline documents. Does not exist as shipped
    # — personalized_rag_service degrades gracefully with no guideline context
    # until real documents are added here (fabricating clinical guideline text
    # ourselves is not an acceptable substitute).
    rag_corpus_dir: str = "guideline_corpus"

    # extra="ignore" so an unrecognised key in .env degrades to a warning-free
    # no-op instead of crashing boot. The previous strict default meant adding
    # GARMIN_EMAIL to .env took the whole API down at import time.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    @property
    def garmin_configured(self) -> bool:
        """
        True only when both credentials look real. Guards against the common
        case of .env carrying the placeholder values from the setup docs, which
        would otherwise burn a login attempt against Garmin for nothing.
        """
        placeholders = {
            "", "you@example.com", "yourpassword",
            "your_email", "your_password", "changeme",
        }
        return (
            self.garmin_email.strip().lower() not in placeholders
            and self.garmin_password.strip() not in placeholders
        )


settings = Settings()
