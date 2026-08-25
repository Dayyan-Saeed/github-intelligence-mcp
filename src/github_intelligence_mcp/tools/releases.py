"""MCP tools for release data."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.releases import get_releases as fetch_releases
from github_intelligence_mcp.models.release import ReleaseResponse
from github_intelligence_mcp.tools._guard import guarded_tool_call
from github_intelligence_mcp.tools.parameters import (
    DEFAULT_LIMIT,
    LimitParam,
    OwnerParam,
    RepoParam,
)


async def get_releases(
    client: GitHubClient,
    owner: str,
    repo: str,
    limit: int = DEFAULT_LIMIT,
) -> list[ReleaseResponse]:
    """Tool implementation: recent releases of a repository."""
    return await guarded_tool_call(
        lambda: fetch_releases(client, owner, repo, limit=limit),
        tool="get_releases",
        owner=owner,
        repo=repo,
        not_found_message=f"Repository '{owner}/{repo}' was not found or is inaccessible.",
    )


def register_release_tools(server: MCPServer, client: GitHubClient) -> None:
    """Register release-related tools on the MCP server."""

    @server.tool(
        name="get_releases",
        title="Get Releases",
        description=(
            "List a repository's most recent releases with tag, name, author, "
            "timestamps, and draft/prerelease flags."
        ),
    )
    async def _get_releases(
        owner: OwnerParam,
        repo: RepoParam,
        limit: LimitParam = DEFAULT_LIMIT,
    ) -> list[ReleaseResponse]:
        return await get_releases(client, owner, repo, limit)
