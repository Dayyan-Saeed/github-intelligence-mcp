"""MCP tools for repository data.

This is the boundary where MCP meets the GitHub client layer: tool
implementations invoke domain operations through the shared guard, which
translates domain errors into clean :class:`ToolError` messages and emits
structured logs.
"""

from __future__ import annotations

from typing import Literal

from mcp.server.mcpserver import MCPServer

from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.repositories import (
    get_repository as fetch_repository,
)
from github_intelligence_mcp.github.repositories import (
    search_repositories as fetch_search_repositories,
)
from github_intelligence_mcp.models.repository import (
    RepositoryResponse,
    SearchRepositoriesResponse,
)
from github_intelligence_mcp.tools._guard import guarded_tool_call
from github_intelligence_mcp.tools.parameters import OwnerParam, RepoParam

SearchSortParam = Literal["stars", "forks", "help-wanted-issues", "updated"]
SearchOrderParam = Literal["asc", "desc"]


async def get_repository(client: GitHubClient, owner: str, repo: str) -> RepositoryResponse:
    """Tool implementation: structured information about one repository."""
    return await guarded_tool_call(
        lambda: fetch_repository(client, owner, repo),
        tool="get_repository",
        owner=owner,
        repo=repo,
        not_found_message=f"Repository '{owner}/{repo}' was not found or is inaccessible.",
    )


async def search_repositories(
    client: GitHubClient,
    query: str,
    *,
    sort: str | None = None,
    order: str = "desc",
    limit: int = 30,
) -> SearchRepositoriesResponse:
    """Tool implementation: search repositories by query."""
    return await guarded_tool_call(
        lambda: fetch_search_repositories(client, query, sort=sort, order=order, limit=limit),
        tool="search_repositories",
    )


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

    @server.tool(
        name="search_repositories",
        title="Search Repositories",
        description=(
            "Search GitHub repositories with a free-form query. Optionally sort "
            "by stars, forks, help-wanted-issues, or updated time, in ascending "
            "or descending order. Returns structured repository summaries."
        ),
    )
    async def _search_repositories(
        query: str,
        sort: SearchSortParam | None = None,
        order: SearchOrderParam = "desc",
        limit: int = 30,
    ) -> SearchRepositoriesResponse:
        return await search_repositories(client, query, sort=sort, order=order, limit=limit)
