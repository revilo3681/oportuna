"""Oportuna configuration. Secrets never leave the server."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPORTUNA_", env_file=".env", extra="ignore")

    app_name: str = "Oportuna"
    environment: str = "development"
    public_site_url: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://oportuna:oportuna@localhost:55432/oportuna"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-only-insecure-secret-change-me-32chars"
    jwt_ttl_hours: int = 24 * 14
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Publication policy (strict auto-publish + human review queue).
    auto_publish_min_confidence: float = 0.70
    auto_publish_max_age_days: int = 21
    review_min_confidence: float = 0.40
    duplicate_review_threshold: float = 0.78
    duplicate_merge_threshold: float = 0.95

    # Ingestion. Conservative defaults: no anti-bot evasion, hard caps per run.
    ingestion_enabled: bool = True
    http_timeout_seconds: int = 20
    http_max_bytes: int = 8_000_000
    http_user_agent: str = "OportunaBot/0.1 (+https://github.com/oportuna; opportunity research; contact: hello@oportuna.dev)"
    ingest_max_items_per_source: int = 120
    ingest_min_interval_seconds: float = 1.0

    seed_admin_email: str | None = None
    seed_admin_password: str | None = None
    demo_mode: bool = False

    scheduler_enabled: bool = True
    ingest_interval_minutes: int = 360
    verify_interval_minutes: int = 60
    digest_hour_utc: int = 12

    # Local AI (Ollama). No external provider required.
    llm_enabled: bool = True
    llm_base_url: str = "http://127.0.0.1:11434"
    llm_model: str = "gemma4:12b-q4"
    llm_embed_model: str = "nomic-embed-text:latest"
    llm_timeout_seconds: int = 180
    llm_temperature: float = 0.2
    llm_max_context_items: int = 6
    llm_max_output_tokens: int = 350
    llm_api_key: str | None = Field(default=None, repr=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
