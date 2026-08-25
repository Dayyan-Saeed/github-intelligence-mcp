"""MCP tools for repository data.

This is the boundary where MCP meets the GitHub client layer: tool
implementations validate inputs, invoke domain operations, translate domain
errors into clean :class:`ToolError` messages, and emit structured logs.

Domain exceptions never escape raw; clients only ever see curated messages.
"""

from __future__ import annotations

import time
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from github_intelligence_mcp.errors import (
    GitHubIntelligenceError,
    GitHubNotFoundError,
    ValidationError,
)
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.repositories import get_repository as fetch_repository
from github_intelligence_mcp.logging import get_logger
from github_intelligence_mcp.models.repository import RepositoryResponse

OwnerParam = Annotated[
    str,
    Field(
        min_length=1, max_length=100, description="Repository owner login (user or organization)."
    ),
]
RepoParam = Annotated[
    str,
    Field(min_length=1, max_length=100, description="Repository name."),
]

_log = get_logger("tools.repositories")


async def get_repository(client: GitHubClient, owner: str, repo: str) -> RepositoryResponse:
    """Tool implementation: structured information about one repository."""
    started = time.perf_counter()
    try:
        result = await fetch_repository(client, owner, repo)
    except GitHubNotFoundError as exc:
        _log.warning(
            "tool=get_repository owner=%s repo=%s status=error reason=not_found",
            owner,
            repo,
        )
        raise ToolError(f"Repository '{owner}/{repo}' was not found or is inaccessible.") from exc
    except ValidationError as exc:
        _log.info(
            "tool=get_repository owner=%s repo=%s status=error reason=invalid_input", owner, repo
        )
        raise ToolError(str(exc)) from exc
    except GitHubIntelligenceError as exc:
        _log.warning(
            "tool=get_repository owner=%s repo=%s status=error reason=%s",
            owner,
            repo,
            type(exc).__name__,
        )
        raise ToolError(str(exc)) from exc

    duration_ms = (time.perf_counter() - started) * 1000
    _log.info(
        "tool=get_repository owner=%s repo=%s status=success duration_ms=%.1f",
        owner,
        repo,
        duration_ms,
    )
    return result


def register_repository_tools(server: MCPServer, client: GitHubClient) -> None:
    """Register repository-related tools on the MCP server."""

    @server.tool(
        name="get_repository",
        title="Get Repository",
        description=(
            "Get detailed, structured information about a GitHub repository, "
            "including stars, forks, watchers, open issues, language, license, "
            "default branch, and activity timestamps."
        ),
    )
    async def _get_repository(owner: OwnerParam, repo: RepoParam) -> RepositoryResponse:
        return await get_repository(client, owner, repo)
