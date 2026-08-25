"""Tests for configuration loading."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from conftest import build_settings
from github_intelligence_mcp.config import Settings


def test_missing_token_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(PydanticValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_defaults(settings: Settings) -> None:
    assert settings.github_api_url == "https://api.github.test"
    assert settings.log_level == "INFO"
    assert settings.request_timeout_seconds == 5.0
    assert settings.cache_enabled is False
    assert settings.cache_ttl_seconds == 300


def test_token_is_secret(settings: Settings) -> None:
    assert "test-token-value" not in repr(settings)
    assert "test-token-value" not in str(settings)
    assert settings.github_token.get_secret_value() == "test-token-value"


def test_log_level_is_normalized() -> None:
    settings = build_settings(log_level="debug")
    assert settings.log_level == "DEBUG"


def test_invalid_log_level_rejected() -> None:
    with pytest.raises(PydanticValidationError):
        build_settings(log_level="chatty")


def test_trailing_slash_stripped_from_api_url() -> None:
    settings = build_settings(github_api_url="https://api.github.test///")
    assert settings.github_api_url == "https://api.github.test"


def test_non_http_api_url_rejected() -> None:
    with pytest.raises(PydanticValidationError):
        build_settings(github_api_url="ftp://api.github.test")


def test_timeout_must_be_positive() -> None:
    with pytest.raises(PydanticValidationError):
        build_settings(request_timeout_seconds=0)


def test_explicit_token_overrides_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    settings = build_settings()
    assert settings.github_token.get_secret_value() == "test-token-value"
    assert "env-token" not in repr(settings)


def test_settings_are_frozen() -> None:
    settings = build_settings()
    with pytest.raises(PydanticValidationError):
        settings.log_level = "DEBUG"
