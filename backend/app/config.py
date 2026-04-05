"""
WarRoom Agent — application configuration.

All settings are loaded from environment variables (or a .env file).
Access the singleton via ``get_settings()``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration backed by env vars / .env file."""

    # ── Database ────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./warroom.db"

    # ── LLM / Anthropic Claude ──────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"

    # ── Slack ───────────────────────────────────────────────────────────
    SLACK_BOT_TOKEN: str = ""
    SLACK_SIGNING_SECRET: str = ""
    SLACK_CHANNEL_ID: str = ""          # Channel to poll for incidents
    SLACK_POLL_INTERVAL: int = 10       # Seconds between polls

    # ── Zoom ────────────────────────────────────────────────────────────
    ZOOM_CLIENT_ID: str = ""
    ZOOM_CLIENT_SECRET: str = ""
    ZOOM_ACCOUNT_ID: str = ""

    # ── Google ──────────────────────────────────────────────────────────
    GOOGLE_SERVICE_ACCOUNT_KEY: str = ""

    # ── SMTP / Email ────────────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""

    # ── Auth0 Core ──────────────────────────────────────────────────────
    AUTH0_DOMAIN: str = ""
    AUTH0_CLIENT_ID: str = ""
    AUTH0_CLIENT_SECRET: str = ""
    AUTH0_AUDIENCE: str = ""
    
    # ── Auth0 FGA ───────────────────────────────────────────
    FGA_API_URL: str = ""
    FGA_STORE_ID: str = ""
    FGA_MODEL_ID: str = ""
    FGA_CLIENT_ID: str = ""
    FGA_CLIENT_SECRET: str = ""
    FGA_API_TOKEN_ISSUER: str = ""
    FGA_API_AUDIENCE: str = ""

    # ── Auth0 Token Vault / Broker ─────────────────────────────────────
    AUTH0_CUSTOM_API_CLIENT_ID: str = ""
    AUTH0_CUSTOM_API_CLIENT_SECRET: str = ""
    AUTH0_TOKEN_ENDPOINT: str = ""
    AUTH0_SLACK_CONNECTION_NAME: str = "sign-in-with-slack"
    AUTH0_GOOGLE_CONNECTION_NAME: str = "google-oauth2"
    
    # ── Github ─────────────────────────────────────
    AUTH0_GITHUB_CONNECTION_NAME: str = "github"

    # ── Auth0 CIBA ──────────────────────────────────────────────────────
    AUTH0_CIBA_ENABLED: bool = False
    AUTH0_CIBA_CLIENT_ID: str = ""
    AUTH0_CIBA_CLIENT_SECRET: str = ""
    AUTH0_CIBA_AUDIENCE: str = ""
    AUTH0_CIBA_SCOPE: str = "openid execute:remediation"
    AUTH0_CIBA_REQUESTED_EXPIRY: int = 300
    AUTH0_CIBA_DEFAULT_POLL_INTERVAL: int = 5
    AUTH0_APP_REMEDIATION_OWNER_SUB: str = ""
    AUTH0_NETWORK_REMEDIATION_OWNER_SUB: str = ""

    # ── JWT ─────────────────────────────────────────────────────────────
    JWT_SECRET: str = "warroom-dev-secret-change-me"

    # ── Application ─────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    APP_ENV: str = "development"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton)."""
    return Settings()
