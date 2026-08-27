"""Tests for MCP resources."""

import respx
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.types import InputRequiredResult

from github_intelligence_mcp.server import create_server


@respx.mock
async def test_all_resource_templates_registered(settings, mock_github) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    templates = await server.list_resource_templates()
    uris = {t.uri_template for t in templates}
    expected = {
        "github://repo/{owner}/{repo}",
        "github://repo/{owner}/{repo}/issues",
        "github://repo/{owner}/{repo}/pulls",
        "github://repo/{owner}/{repo}/commits",
        "github://repo/{owner}/{repo}/contributors",
        "github://repo/{owner}/{repo}/releases",
    }
    assert expected == uris


@respx.mock
async def test_repo_resource_readable(settings, mock_github) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    result = await server.read_resource("github://repo/o/r")
    assert not isinstance(result, InputRequiredResult)
    contents = list(result)
    assert len(contents) >= 1
    assert isinstance(contents[0], ReadResourceContents)
    text = contents[0].content
    assert "octocat" in text or "Test" in text or "description" in text


@respx.mock
async def test_issues_resource_readable(settings, mock_github) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    result = await server.read_resource("github://repo/o/r/issues")
    assert not isinstance(result, InputRequiredResult)
    contents = list(result)
    assert len(contents) >= 1
    assert isinstance(contents[0], ReadResourceContents)
    text = contents[0].content
    assert "issue" in text.lower() or "number" in text.lower() or "[]" in text
