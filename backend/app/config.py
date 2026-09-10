"""Application configuration.

Settings load from environment variables, optionally via a local .env file.
See backend/.env.example for the supported keys. No secrets belong in this file.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the AEGIS backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Identity
    SERVICE_NAME: str = "aegis-backend"
    VERSION: str = "0.2.0"
    PHASE: str = "1 - security engine"
    ENVIRONMENT: str = "development"

    # Persistence
    DATABASE_URL: str = "sqlite:///./aegis.db"

    # Auth
    JWT_SECRET: str = "dev-only-insecure-secret-change-me"
    TOKEN_TTL_MINUTES: int = 240
    APPROVAL_TTL_SECONDS: int = 180

    # Observability
    LOG_LEVEL: str = "INFO"

    # HTTP
    API_PREFIX: str = "/api"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()
