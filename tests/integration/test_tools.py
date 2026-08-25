"""Integration-style tests for MCP tool invocation.

These exercise the real MCPServer instance end-to-end (schema generation,
input validation, tool dispatch, structured output, error translation) with
the GitHub API fully mocked via respx. No network access and no real token.

Note on error semantics: when ``MCPServer.call_tool`` is invoked directly
in-process, anticipated tool failures raise :class:`ToolError` whose message
is exactly what a session-based MCP client would receive as an ``is_error``
result. These tests assert against that raised message.
"""

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


def _payload(name: str) -> Any:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


async def test_get_repository_is_registered(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    tools = await server.list_tools()
    names = {tool.name for tool in tools}
    assert "get_repository" in names

    tool = next(t for t in tools if t.name == "get_repository")
    schema_properties = set(tool.input_schema["properties"])
    assert {"owner", "repo"} <= schema_properties
    assert tool.description


@respx.mock
async def test_get_repository_returns_structured_data(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/facebook/react").mock(
        return_value=httpx.Response(200, json=_payload("repository.json"))
    )
    server = create_server(settings)

    result = await server.call_tool("get_repository", {"owner": "facebook", "repo": "react"})

    assert isinstance(result, CallToolResult)
    assert not result.is_error
    text = " ".join(getattr(block, "text", "") or "" for block in result.content)
    assert "facebook/react" in text
    assert "238000" in text  # stars


@respx.mock
async def test_get_repository_translates_not_found(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/foo/bar").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    server = create_server(settings)

    with pytest.raises(ToolError, match=r"Repository 'foo/bar' was not found"):
        await server.call_tool("get_repository", {"owner": "foo", "repo": "bar"})


async def test_get_repository_rejects_invalid_owner(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)

    with pytest.raises(ToolError, match="valid GitHub username"):
        await server.call_tool("get_repository", {"owner": "../evil", "repo": "react"})


@respx.mock
async def test_get_repository_translates_rate_limit_error(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/facebook/react").mock(
        return_value=httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1790000000"},
            json={"message": "API rate limit exceeded"},
        )
    )
    server = create_server(settings)

    with pytest.raises(ToolError, match="rate limit exceeded"):
        await server.call_tool("get_repository", {"owner": "facebook", "repo": "react"})


@respx.mock
async def test_tool_output_never_contains_token(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/facebook/react").mock(
        return_value=httpx.Response(401, json={"message": "Bad credentials"})
    )
    server = create_server(settings)

    with pytest.raises(ToolError) as excinfo:
        await server.call_tool("get_repository", {"owner": "facebook", "repo": "react"})

    assert "test-token-value" not in str(excinfo.value)


# ---------------------------------------------------------------------------
# search_repositories
# ---------------------------------------------------------------------------


async def test_search_repositories_is_registered(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    tools = await server.list_tools()
    names = {tool.name for tool in tools}
    assert "search_repositories" in names

    tool = next(t for t in tools if t.name == "search_repositories")
    properties = tool.input_schema["properties"]
    sort_variants = [
        {"enum": properties["sort"].get("enum", [])},
        *properties["sort"].get("anyOf", []),
    ]
    sort_values = {value for v in sort_variants for value in v.get("enum", [])}
    assert sort_values == {"stars", "forks", "help-wanted-issues", "updated"}


@respx.mock
async def test_search_repositories_returns_summaries(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/search/repositories").mock(
        return_value=httpx.Response(200, json=_payload("search_repositories.json"))
    )
    server = create_server(settings)

    result = await server.call_tool(
        "search_repositories", {"query": "language:javascript", "limit": 2}
    )

    assert isinstance(result, CallToolResult)
    assert not result.is_error
    text = " ".join(getattr(block, "text", "") or "" for block in result.content)
    assert "facebook/react" in text
    assert "vuejs/vue" in text


async def test_search_repositories_rejects_bad_sort_via_schema(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)

    with pytest.raises(ToolError, match="search_repositories"):
        await server.call_tool("search_repositories", {"query": "react", "sort": "cuteness"})
