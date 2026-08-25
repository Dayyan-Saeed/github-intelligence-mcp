"""Shared test fixtures."""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from pydantic import SecretStr

from github_intelligence_mcp.config import Settings
from github_intelligence_mcp.github.client import GitHubClient


def build_settings(**overrides: Any) -> Settings:
    """Construct deterministic settings for tests.

    Environment variable and ``.env`` lookups are disabled so tests never
    depend on machine state.
    """
    values: dict[str, Any] = {
        "github_token": SecretStr("test-token-value"),
        "github_api_url": "https://api.github.test",
        "request_timeout_seconds": 5.0,
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def settings() -> Settings:
    """Default settings used across unit and integration tests."""
    return build_settings()


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[GitHubClient]:
    """GitHub client with near-instant backoff for fast retry tests."""
    async with GitHubClient(settings, backoff_base_seconds=0.001) as github_client:
        yield github_client
