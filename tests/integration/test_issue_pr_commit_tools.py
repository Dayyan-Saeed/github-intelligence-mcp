"""Integration tests for the get_issues, get_pull_requests, and get_recent_commits tools."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult

from github_intelligence_mcp.server import create_server

FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"
BASE_URL = "https://api.github.test"


def _load(name: str) -> list[Any] | dict[str, Any]:
    value = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(value, (list, dict))
    return value


async def test_all_registered_tools(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    names = {tool.name for tool in await server.list_tools()}
    expected = {
        "get_repository",
        "search_repositories",
        "get_issues",
        "get_pull_requests",
        "get_recent_commits",
        "get_contributors",
        "get_releases",
        "analyze_repository",
        "find_maintenance_risks",
        "compare_repositories",
    }
    assert names == expected


# ---------------------------------------------------------------------------
# get_issues
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_issues_returns_structured_list(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/facebook/react/issues").mock(
        return_value=httpx.Response(200, json=_load("issues.json"))
    )
    server = create_server(settings)

    result = await server.call_tool(
        "get_issues", {"owner": "facebook", "repo": "react", "state": "all", "limit": 10}
    )

    assert isinstance(result, CallToolResult)
    assert not result.is_error
    text = " ".join(getattr(block, "text", "") or "" for block in result.content)
    assert "hydration mismatch" in text
    assert "pull/14018" not in text  # PR entry filtered out


@respx.mock
async def test_get_issues_translates_not_found(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/foo/bar/issues").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    server = create_server(settings)

    with pytest.raises(ToolError, match=r"Repository 'foo/bar' was not found"):
        await server.call_tool("get_issues", {"owner": "foo", "repo": "bar"})


async def test_get_issues_rejects_invalid_state_via_schema(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)

    with pytest.raises(ToolError, match="get_issues"):
        await server.call_tool(
            "get_issues", {"owner": "facebook", "repo": "react", "state": "sometimes"}
        )


# ---------------------------------------------------------------------------
# get_pull_requests
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_pull_requests_returns_structured_list(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/facebook/react/pulls").mock(
        return_value=httpx.Response(200, json=_load("pull_requests.json"))
    )
    server = create_server(settings)

    result = await server.call_tool("get_pull_requests", {"owner": "facebook", "repo": "react"})

    assert isinstance(result, CallToolResult)
    assert not result.is_error
    text = " ".join(getattr(block, "text", "") or "" for block in result.content)
    assert "suspense" in text
    assert "30100" in text


# ---------------------------------------------------------------------------
# get_recent_commits
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_recent_commits_returns_structured_list(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/facebook/react/commits").mock(
        return_value=httpx.Response(200, json=_load("commits.json"))
    )
    server = create_server(settings)

    result = await server.call_tool(
        "get_recent_commits", {"owner": "facebook", "repo": "react", "days": 14}
    )

    assert isinstance(result, CallToolResult)
    assert not result.is_error
    text = " ".join(getattr(block, "text", "") or "" for block in result.content)
    assert "useSyncExternalStore" in text
    assert "acdlite" in text


@respx.mock
async def test_get_recent_commits_translates_rate_limit(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/facebook/react/commits").mock(
        return_value=httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1790000000"},
            json={"message": "API rate limit exceeded"},
        )
    )
    server = create_server(settings)

    with pytest.raises(ToolError, match="rate limit"):
        await server.call_tool("get_recent_commits", {"owner": "facebook", "repo": "react"})
