"""Integration tests for the analyze_repository tool."""

import httpx
import pytest
import respx
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult

from conftest import BASE_URL
from github_intelligence_mcp.server import create_server

COMPONENT_NAMES = (
    "activity",
    "issue_health",
    "pr_health",
    "contributor_health",
    "release_activity",
    "documentation",
)


async def test_analyze_repository_is_registered(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    names = {tool.name for tool in await server.list_tools()}
    assert {"analyze_repository", "find_maintenance_risks"} <= names


@respx.mock
async def test_find_maintenance_risks_returns_report(settings, mock_github) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)

    result = await server.call_tool("find_maintenance_risks", {"owner": "o", "repo": "r"})

    assert isinstance(result, CallToolResult)
    assert not result.is_error
    text = " ".join(getattr(block, "text", "") or "" for block in result.content)
    assert '"risk_level"' in text.replace("risk_level", '"risk_level"') or "risk_level" in text
    assert "stale_issues" in text  # fixture backlog contains a 200-day-old issue
    assert "evidence" in text


async def test_analyze_repository_returns_health_report(settings, mock_github) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)

    result = await server.call_tool("analyze_repository", {"owner": "o", "repo": "r"})

    assert isinstance(result, CallToolResult)
    assert not result.is_error
    text = " ".join(getattr(block, "text", "") or "" for block in result.content)
    assert "overall" in text
    assert '"grade"' in text.replace("grade", '"grade"') or "grade" in text.lower()
    for component in COMPONENT_NAMES:
        assert component in text


@respx.mock
async def test_analyze_repository_translates_not_found(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/foo/bar").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    server = create_server(settings)

    with pytest.raises(ToolError, match=r"Repository 'foo/bar' was not found"):
        await server.call_tool("analyze_repository", {"owner": "foo", "repo": "bar"})
