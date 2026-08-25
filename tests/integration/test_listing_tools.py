"""Integration tests for the get_contributors and get_releases tools."""

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


# ---------------------------------------------------------------------------
# get_contributors
# ---------------------------------------------------------------------------


async def test_get_contributors_is_registered(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    names = {tool.name for tool in await server.list_tools()}
    assert "get_contributors" in names


@respx.mock
async def test_get_contributors_returns_structured_list(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/facebook/react/contributors").mock(
        return_value=httpx.Response(200, json=_load("contributors.json"))
    )
    server = create_server(settings)

    result = await server.call_tool(
        "get_contributors", {"owner": "facebook", "repo": "react", "limit": 10}
    )

    assert isinstance(result, CallToolResult)
    assert not result.is_error
    text = " ".join(getattr(block, "text", "") or "" for block in result.content)
    assert "gaearon" in text
    assert "Anonymous Contributor" not in text  # login-less entries are skipped


@respx.mock
async def test_get_contributors_translates_not_found(settings) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/foo/bar/contributors").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    server = create_server(settings)

    with pytest.raises(ToolError, match=r"Repository 'foo/bar' was not found"):
        await server.call_tool("get_contributors", {"owner": "foo", "repo": "bar"})


async def test_get_contributors_enforces_limit_bounds(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)

    with pytest.raises(ToolError, match="get_contributors"):
        await server.call_tool(
            "get_contributors", {"owner": "facebook", "repo": "react", "limit": 0}
        )


# ---------------------------------------------------------------------------
# get_releases
# ---------------------------------------------------------------------------


async def test_get_releases_is_registered(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    names = {tool.name for tool in await server.list_tools()}
    assert "get_releases" in names


@respx.mock
async def test_get_releases_returns_structured_list(settings) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/repos/facebook/react/releases").mock(
        side_effect=[
            httpx.Response(200, json=_load("releases.json")),
            httpx.Response(200, json=[]),
        ]
    )
    server = create_server(settings)

    result = await server.call_tool(
        "get_releases", {"owner": "facebook", "repo": "react", "limit": 100}
    )

    assert isinstance(result, CallToolResult)
    assert not result.is_error
    text = " ".join(getattr(block, "text", "") or "" for block in result.content)
    assert "v19.1.0" in text
    assert "v19.2.0-rc1" in text

    last_params = dict(route.calls.last.request.url.params)
    assert last_params["per_page"] == "100"
