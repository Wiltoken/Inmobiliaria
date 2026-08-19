"""Pydantic settings — all auth policy values as named parameters, zero hardcoded literals."""

from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """All security thresholds and connection strings as typed pydantic-settings fields."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── REQUIRED ──────────────────────────────────────────────────────────────
    secret_key: str = Field(default="", description="JWT signing key. REQUIRED in production.")

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://authuser:changeme@localhost:5432/auth_db",
        description="Async PostgreSQL DSN using asyncpg driver.",
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis DSN for session blacklist, rate limiting, and refresh tokens.",
    )

    # ── Security: Login & Lockout ─────────────────────────────────────────────
    max_login_attempts: int = Field(default=3, description="Failed attempts before account lockout.")
    lockout_duration_minutes: int = Field(default=15, description="Lockout duration in minutes.")

    # ── Security: Tokens ───────────────────────────────────────────────────────
    access_token_expire_minutes: int = Field(default=15, description="Access token TTL in minutes.")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token TTL in days.")
    inactivity_timeout_minutes: int = Field(default=30, description="Session inactivity timeout in minutes.")

    # ── Security: Password Policy ─────────────────────────────────────────────
    password_min_length: int = Field(default=8, ge=1, le=256, description="Minimum password length.")
    password_require_special: bool = Field(default=True, description="Require at least one special character.")
    password_expiry_days: int = Field(default=30, ge=0, description="Days before password expires. 0 = never.")

    # ── Security: reCAPTCHA v3 ────────────────────────────────────────────────
    recaptcha_enabled: bool = Field(default=False, description="Enable Google reCAPTCHA v3 verification.")
    recaptcha_score_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum acceptable reCAPTCHA score."
    )
    recaptcha_site_key: str = Field(default="", description="reCAPTCHA v3 site key.")
    recaptcha_secret_key: str = Field(default="", description="reCAPTCHA v3 secret key.")

    # ── Security: Anti-clipboard paste ────────────────────────────────────────
    copy_paste_restricted: bool = Field(
        default=False,
        description="Prevent clipboard paste in password field (UI-layer enforcement hint).",
    )

    # ── Compliance: Colombian Ley 1581/2012 ───────────────────────────────────
    audit_retention_days: int = Field(
        default=365, ge=1, description="Audit log retention in days. Minimum required by Ley 1581."
    )

    # ── Rate Limiting ──────────────────────────────────────────────────────────
    rate_limit_requests_per_second: int = Field(
        default=5, ge=1, description="Token bucket rate: requests per second."
    )
    rate_limit_window_seconds: int = Field(
        default=1, ge=1, description="Token bucket window in seconds."
    )

    # ── SMTP Notification ──────────────────────────────────────────────────────
    smtp_host: str = Field(default="localhost", description="SMTP server hostname.")
    smtp_port: int = Field(default=587, ge=1, le=65535, description="SMTP port.")
    smtp_user: str = Field(default="", description="SMTP username.")
    smtp_password: str = Field(default="", description="SMTP password.")
    smtp_from: str = Field(default="noreply@auth.local", description="From address for outgoing emails.")

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = Field(default="development", description="Runtime environment.")
    log_level: str = Field(default="INFO", description="Logging level.")
    app_base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for the application (used in email links).",
    )

    # ── Matching ──────────────────────────────────────────────────────────────
    match_cache_ttl_seconds: int = Field(
        default=3600,
        ge=1,
        description="TTL for cached match results in Redis (seconds).",
    )

    @field_validator("secret_key")
    @classmethod
    def secret_key_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("SECRET_KEY is required. Generate with: python -c 'import secrets; print(secrets.token_urlsafe(64))'")
        return v

    @field_validator("log_level")
    @classmethod
    def log_level_valid(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(valid))}")
        return v.upper()


class YAMLConfigLoader:
    """Loads config.yaml (optional) and maps its values into pydantic-settings at startup.

    Deferred from design ADR-006. If config.yaml is absent, env-only config works fine.
    The YAML file provides a human-friendly per-deployment override layer.

    Usage:
        settings = YAMLConfigLoader().load(AuthSettings)
    """

    def load(self, settings_cls: type[BaseSettings], config_path: str | Path = "config.yaml") -> BaseSettings:
        data: dict[str, Any] = {}

        cfg = Path(config_path)
        if cfg.exists():
            with cfg.open() as fh:
                raw = yaml.safe_load(fh) or {}

            # Top-level modules block mirrors the named parameter names directly
            data = raw.get("modules", {})

            # Also accept top-level keys for simple deployments
            for key in dir(settings_cls):
                if key in raw and key.isidentifier():
                    data.setdefault(key, raw[key])

        if data:
            return settings_cls(**data)
        return settings_cls()


@lru_cache
def get_settings() -> AuthSettings:
    """Cached singleton settings instance."""
    return AuthSettings()


# Convenience alias
settings = get_settings()


# Default tenant for single-tenant deployments (zero UUID).
# Shared by login, registration, and the seed script so all auth/demo data
# lives in one tenant.
DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")
