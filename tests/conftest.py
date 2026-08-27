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

from github_intelligence_mcp.analysis.analyzer import AnalysisSnapshot
from github_intelligence_mcp.config import Settings
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.issues import build_issue_response
from github_intelligence_mcp.github.pull_requests import build_pull_request_response
from github_intelligence_mcp.github.repositories import build_repository_response
from github_intelligence_mcp.models.commit import CommitResponse
from github_intelligence_mcp.models.contributor import ContributorResponse
from github_intelligence_mcp.models.release import ReleaseResponse

BASE_URL = "https://api.github.test"
FIXTURES_DIR = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

SnapshotOverrides = dict[str, Any]
AnalysisSnapshotFactory = Any  # refined below via annotation in the fixture


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


def _commit_model(author: str | None, *, days_ago: int) -> CommitResponse:
    when = NOW - timedelta(days=days_ago)
    return CommitResponse(
        sha=f"sha-{author}-{days_ago}",
        message="test commit",
        author=author,
        author_date=when,
        committer=author,
        commit_date=when,
        html_url="https://github.test/o/r/commit/x",
    )


@pytest.fixture
def snapshot_factory() -> Any:
    """Build :class:`AnalysisSnapshot` instances with healthy defaults.

    ``None`` means "keep the healthy default"; pass an explicit list to
    override. The default snapshot triggers no maintenance risks.
    """

    def _factory(
        *,
        now: datetime | None = None,
        pushed_days_ago: int = 3,
        open_issues: list[dict[str, Any]] | None = None,
        closed_issues: list[dict[str, Any]] | None = None,
        open_pulls: list[dict[str, Any]] | None = None,
        closed_pulls: list[dict[str, Any]] | None = None,
        commits_authors: list[str] | None = None,
        commits_last_30: list[CommitResponse] | None = None,
        commits_last_90: list[CommitResponse] | None = None,
        contributors: list[dict[str, Any]] | None = None,
        releases: list[dict[str, Any]] | None = None,
    ) -> AnalysisSnapshot:
        clock = now or NOW
        metadata_payload = load_fixture("repository.json")
        metadata = build_repository_response(metadata_payload)
        pushed_at = clock - timedelta(days=pushed_days_ago)

        authors = ["alice", "bob", "carol"] if commits_authors is None else commits_authors
        resolved_commits_30 = (
            [_commit_model(a, days_ago=5) for a in authors]
            if commits_last_30 is None
            else commits_last_30
        )
        resolved_commits_90 = (
            [_commit_model(a, days_ago=40) for a in authors]
            if commits_last_90 is None
            else commits_last_90
        )
        resolved_contributors = (
            [
                contributor_payload("alice", 10),
                contributor_payload("bob", 10),
                contributor_payload("carol", 10),
            ]
            if contributors is None
            else contributors
        )
        resolved_releases = [release_payload(30, "v1.0")] if releases is None else releases

        return AnalysisSnapshot(
            owner="o",
            repo="r",
            now=clock,
            metadata=metadata.model_copy(update={"pushed_at": pushed_at}),
            has_readme=True,
            open_issues=[build_issue_response(i) for i in (open_issues or [])],
            closed_issues=[build_issue_response(i) for i in (closed_issues or [])],
            open_pulls=[build_pull_request_response(p) for p in (open_pulls or [])],
            closed_pulls=[build_pull_request_response(p) for p in (closed_pulls or [])],
            commits_30=resolved_commits_30,
            commits_90=resolved_commits_90,
            contributors=[
                ContributorResponse(
                    username=c["login"],
                    contributions=c["contributions"],
                    avatar_url=c["avatar_url"],
                    html_url=c["html_url"],
                )
                for c in resolved_contributors
            ],
            releases=[
                ReleaseResponse(
                    tag_name=r["tag_name"],
                    name=r.get("name"),
                    author=(r.get("author") or {}).get("login"),
                    created_at=datetime.fromisoformat(r["created_at"]),
                    published_at=(
                        datetime.fromisoformat(r["published_at"]) if r.get("published_at") else None
                    ),
                    prerelease=r.get("prerelease", False),
                    draft=r.get("draft", False),
                    html_url=r["html_url"],
                )
                for r in resolved_releases
            ],
        )

    return _factory
