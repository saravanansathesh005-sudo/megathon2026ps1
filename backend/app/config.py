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
    VERSION: str = "0.3.0"
    PHASE: str = "3 - gemini + oauth + terminal"
    ENVIRONMENT: str = "development"

    # Persistence
    DATABASE_URL: str = "sqlite:///./aegis.db"

    # Auth
    JWT_SECRET: str = "dev-only-insecure-secret-change-me"
    TOKEN_TTL_MINUTES: int = 240
    APPROVAL_TTL_SECONDS: int = 180

    # Gemini planning layer. Absent key -> deterministic fallback planner.
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_TIMEOUT_SECONDS: int = 12

    # Google OAuth. Absent client id -> Google sign-in unavailable.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # Demo password login for the seeded accounts. Refused when ENVIRONMENT=production.
    ALLOW_PASSWORD_LOGIN: bool = True

    # Observability
    LOG_LEVEL: str = "INFO"

    # HTTP
    API_PREFIX: str = "/api"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()
