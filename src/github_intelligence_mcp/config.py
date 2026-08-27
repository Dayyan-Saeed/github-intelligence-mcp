"""Typed application configuration loaded from environment variables.

Required environment variables:

- ``GITHUB_TOKEN``

Optional environment variables:

- ``GITHUB_API_URL``
- ``LOG_LEVEL``
- ``REQUEST_TIMEOUT_SECONDS``
- ``CACHE_ENABLED`` (reserved for Phase 4 caching)
- ``CACHE_TTL_SECONDS`` (reserved for Phase 4 caching)

Secrets are never hardcoded and never logged; the token is stored as a
:class:`~pydantic.SecretStr` so accidental repr/str interpolation stays redacted.
"""

from __future__ import annotations

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_GITHUB_API_URL = "https://api.github.com"

_ALLOWED_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class Settings(BaseSettings):
    """Application settings sourced from environment variables and ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    github_token: SecretStr = Field(
        description="GitHub personal access token used for API authentication.",
    )
    github_api_url: str = Field(
        default=DEFAULT_GITHUB_API_URL,
        description="Root URL of the GitHub REST API.",
    )
    log_level: str = Field(
        default="INFO",
        description="Application log level.",
    )
    request_timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        le=120.0,
        description="Per-request HTTP timeout in seconds.",
    )
    cache_enabled: bool = Field(
        default=False,
        description="Whether response caching is enabled.",
    )
    cache_backend: str = Field(
        default="memory",
        description="Cache backend: 'memory' for in-process, 'sqlite' for persistent.",
    )
    cache_path: str = Field(
        default=".cache/github-intelligence.db",
        description="Filesystem path for the SQLite cache (ignored for memory backend).",
    )
    cache_ttl_seconds: int = Field(
        default=300,
        gt=0,
        description="Default cache TTL in seconds (overridden by per-endpoint defaults).",
    )
    stale_issue_days: int = Field(
        default=90,
        ge=1,
        description="An open issue untouched for this many days counts as stale.",
    )
    stale_pr_days: int = Field(
        default=30,
        ge=1,
        description="An open pull request untouched for this many days counts as stale.",
    )

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in _ALLOWED_LOG_LEVELS:
            allowed = ", ".join(sorted(_ALLOWED_LOG_LEVELS))
            raise ValueError(f"log_level must be one of: {allowed}")
        return normalized

    @field_validator("github_api_url")
    @classmethod
    def _validate_api_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("github_api_url must be an http(s) URL")
        return normalized


def load_settings() -> Settings:
    """Load settings from the environment (and ``.env`` if present).

    Raises a clear :class:`pydantic.ValidationError` when ``GITHUB_TOKEN``
    is missing.
    """
    # The token arrives via the environment at runtime, so the constructor
    # argument is intentionally absent here.
    return Settings()  # type: ignore[call-arg]
