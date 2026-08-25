"""MCP tools for contributor data."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.contributors import (
    get_contributors as fetch_contributors,
)
from github_intelligence_mcp.models.contributor import ContributorResponse
from github_intelligence_mcp.tools._guard import guarded_tool_call
from github_intelligence_mcp.tools.parameters import (
    DEFAULT_LIMIT,
    LimitParam,
    OwnerParam,
    RepoParam,
)


async def get_contributors(
    client: GitHubClient,
    owner: str,
    repo: str,
    limit: int = DEFAULT_LIMIT,
) -> list[ContributorResponse]:
    """Tool implementation: the most active contributors of a repository."""
    return await guarded_tool_call(
        lambda: fetch_contributors(client, owner, repo, limit=limit),
        tool="get_contributors",
        owner=owner,
        repo=repo,
        not_found_message=f"Repository '{owner}/{repo}' was not found or is inaccessible.",
    )


def register_contributor_tools(server: MCPServer, client: GitHubClient) -> None:
    """Register contributor-related tools on the MCP server."""

    @server.tool(
        name="get_contributors",
        title="Get Contributors",
        description=(
            "List a repository's contributors ordered by contribution count, "
            "with username and total contributions."
        ),
    )
    async def _get_contributors(
        owner: OwnerParam,
        repo: RepoParam,
        limit: LimitParam = DEFAULT_LIMIT,
    ) -> list[ContributorResponse]:
        return await get_contributors(client, owner, repo, limit)
