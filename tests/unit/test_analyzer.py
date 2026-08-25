"""Tests for the repository analysis orchestrator."""

from datetime import UTC, datetime

import pytest
import respx
from httpx import Response

from conftest import BASE_URL, NOW, load_fixture
from github_intelligence_mcp.analysis.analyzer import analyze_repository
from github_intelligence_mcp.errors import GitHubNotFoundError


async def test_analyze_repository_returns_all_components(client, mock_github) -> None:  # type: ignore[no-untyped-def]
    result = await analyze_repository(client, "o", "r", now=NOW)

    assert result.owner == "o"
    assert result.repo == "r"
    assert result.computed_at == NOW
    assert {c.name for c in result.components} == {
        "activity",
        "issue_health",
        "pr_health",
        "contributor_health",
        "release_activity",
        "documentation",
    }
    assert 0 <= result.overall_score <= 100
    assert result.grade in {"A", "B", "C", "D", "F"}
    weights_total = sum(c.weight for c in result.components)
    assert weights_total == pytest.approx(1.0)


async def test_analyze_repository_documentation_component_is_exact(client, mock_github) -> None:  # type: ignore[no-untyped-def]
    result = await analyze_repository(client, "o", "r", now=NOW)

    docs = next(c for c in result.components if c.name == "documentation")
    assert docs.score == 100  # README + license + description + homepage all present
    assert docs.details["has_readme"] is True


async def test_analyze_repository_issue_evidence_counts_stale(client, mock_github) -> None:  # type: ignore[no-untyped-def]
    result = await analyze_repository(client, "o", "r", now=NOW)

    issues = next(c for c in result.components if c.name == "issue_health")
    assert issues.details["open_issue_count"] == 3
    assert issues.details["stale_issue_count"] == 1  # issue #3 at 200 days
    assert issues.details["closed_last_90"] == 1


async def test_analyze_repository_pr_evidence_counts_stale_and_merged(client, mock_github) -> None:  # type: ignore[no-untyped-def]
    result = await analyze_repository(client, "o", "r", now=NOW)

    prs = next(c for c in result.components if c.name == "pr_health")
    assert prs.details["open_pull_request_count"] == 2
    assert prs.details["stale_pull_request_count"] == 1  # 60-day-old open PR
    assert prs.details["merged_last_90"] == 1


async def test_analyze_repository_activity_reflects_sampled_commits(client, mock_github) -> None:  # type: ignore[no-untyped-def]
    result = await analyze_repository(client, "o", "r", now=NOW)

    activity = next(c for c in result.components if c.name == "activity")
    assert activity.details["commits_last_30"] == 2  # from commits fixture
    assert activity.details["active_contributors_last_30"] == 2


@respx.mock
async def test_analyze_repository_missing_readme_lowers_documentation(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/o/r").mock(
        return_value=Response(200, json=load_fixture("repository.json"))
    )
    respx.get(f"{BASE_URL}/repos/o/r/readme").mock(return_value=Response(404))
    for path in ("issues", "pulls", "commits", "contributors", "releases"):
        respx.get(f"{BASE_URL}/repos/o/r/{path}").mock(return_value=Response(200, json=[]))

    result = await analyze_repository(client, "o", "r", now=NOW)

    docs = next(c for c in result.components if c.name == "documentation")
    assert docs.score < 100
    assert docs.details["has_readme"] is False


@respx.mock
async def test_analyze_repository_translates_not_found(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/foo/bar").mock(
        return_value=Response(404, json={"message": "Not Found"})
    )

    with pytest.raises(GitHubNotFoundError):
        await analyze_repository(client, "foo", "bar", now=datetime.now(UTC))
