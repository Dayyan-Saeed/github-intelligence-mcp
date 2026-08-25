"""Shared test fixtures."""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from pydantic import SecretStr

from github_intelligence_mcp.config import Settings
from github_intelligence_mcp.github.client import GitHubClient

BASE_URL = "https://api.github.test"
FIXTURES_DIR = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


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


def load_fixture(name: str) -> Any:
    """Load a canned JSON fixture from ``tests/fixtures``."""
    value = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(value, (list, dict))
    return value


# ---------------------------------------------------------------------------
# GitHub payload builders for analysis mocks (relative to NOW)
# ---------------------------------------------------------------------------


def issue_payload(
    number: int, *, created_days_ago: int, updated_days_ago: int | None = None
) -> dict[str, Any]:
    created = NOW - timedelta(days=created_days_ago)
    updated = NOW - timedelta(
        days=updated_days_ago if updated_days_ago is not None else created_days_ago
    )
    return {
        "number": number,
        "title": f"issue {number}",
        "state": "open",
        "user": {"login": f"user{number}"},
        "created_at": created.isoformat(),
        "updated_at": updated.isoformat(),
        "closed_at": None,
        "labels": [],
        "html_url": f"https://github.test/o/r/issues/{number}",
    }


def closed_issue_payload(number: int, *, closed_days_ago: int) -> dict[str, Any]:
    payload = issue_payload(number, created_days_ago=closed_days_ago + 5)
    closed = NOW - timedelta(days=closed_days_ago)
    payload["state"] = "closed"
    payload["closed_at"] = closed.isoformat()
    return payload


def open_pr_payload(number: int, *, created_days_ago: int) -> dict[str, Any]:
    created = NOW - timedelta(days=created_days_ago)
    return {
        "number": number,
        "title": f"pr {number}",
        "state": "open",
        "draft": False,
        "user": {"login": f"dev{number}"},
        "created_at": created.isoformat(),
        "updated_at": created.isoformat(),
        "closed_at": None,
        "merged_at": None,
        "labels": [],
        "html_url": f"https://github.test/o/r/pull/{number}",
    }


def merged_pr_payload(number: int, *, merged_days_ago: int) -> dict[str, Any]:
    payload = open_pr_payload(number, created_days_ago=merged_days_ago + 3)
    merged = NOW - timedelta(days=merged_days_ago)
    payload["state"] = "closed"
    payload["closed_at"] = merged.isoformat()
    payload["merged_at"] = merged.isoformat()
    return payload


def release_payload(days_ago: int, tag: str) -> dict[str, Any]:
    published = NOW - timedelta(days=days_ago)
    return {
        "tag_name": tag,
        "name": tag,
        "author": {"login": "releaser"},
        "created_at": published.isoformat(),
        "published_at": published.isoformat(),
        "prerelease": False,
        "draft": False,
        "html_url": f"https://github.test/o/r/releases/tag/{tag}",
    }


def contributor_payload(name: str, contributions: int) -> dict[str, Any]:
    return {
        "login": name,
        "contributions": contributions,
        "avatar_url": "https://a.test/x.png",
        "html_url": f"https://github.test/{name}",
    }


@pytest.fixture
def mock_github() -> Any:
    """Mock every endpoint the analyzer touches for repository ``o/r``.

    Activation is scoped to this fixture (setup through teardown), so routes
    never leak into other tests. Tests using this fixture do NOT need
    ``@respx.mock``.
    """
    with respx.mock:
        repo_payload = load_fixture("repository.json")

        respx.get(f"{BASE_URL}/repos/o/r").mock(return_value=httpx.Response(200, json=repo_payload))
        respx.get(f"{BASE_URL}/repos/o/r/readme").mock(return_value=httpx.Response(200, json={}))

        open_issues = [
            issue_payload(1, created_days_ago=10),
            issue_payload(2, created_days_ago=40),
            issue_payload(3, created_days_ago=200),
        ]
        closed_issues = [closed_issue_payload(11, closed_days_ago=10)]
        respx.get(f"{BASE_URL}/repos/o/r/issues", params={"state": "open"}).mock(
            return_value=httpx.Response(200, json=open_issues)
        )
        respx.get(f"{BASE_URL}/repos/o/r/issues", params={"state": "closed"}).mock(
            return_value=httpx.Response(200, json=closed_issues)
        )

        open_pulls = [
            open_pr_payload(21, created_days_ago=5),
            open_pr_payload(22, created_days_ago=60),
        ]
        closed_pulls = [merged_pr_payload(31, merged_days_ago=20)]
        respx.get(f"{BASE_URL}/repos/o/r/pulls", params={"state": "open"}).mock(
            return_value=httpx.Response(200, json=open_pulls)
        )
        respx.get(f"{BASE_URL}/repos/o/r/pulls", params={"state": "closed"}).mock(
            return_value=httpx.Response(200, json=closed_pulls)
        )

        respx.get(f"{BASE_URL}/repos/o/r/commits").mock(
            return_value=httpx.Response(200, json=load_fixture("commits.json"))
        )
        respx.get(f"{BASE_URL}/repos/o/r/contributors").mock(
            return_value=httpx.Response(
                200,
                json=[contributor_payload("gaearon", 900), contributor_payload("helper", 100)],
            )
        )
        respx.get(f"{BASE_URL}/repos/o/r/releases").mock(
            return_value=httpx.Response(
                200,
                json=[
                    release_payload(15, "v1.2"),
                    release_payload(45, "v1.1"),
                    release_payload(75, "v1.0"),
                ],
            )
        )
        yield
