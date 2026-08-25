"""MCP tools for commit data."""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.commits import get_recent_commits as fetch_recent_commits
from github_intelligence_mcp.models.commit import CommitResponse
from github_intelligence_mcp.tools._guard import guarded_tool_call
from github_intelligence_mcp.tools.parameters import (
    DEFAULT_LIMIT,
    LimitParam,
    OwnerParam,
    RepoParam,
)

DaysParam = Annotated[
    int, Field(ge=1, le=365, description="How many days back to look for commits.")
]


async def get_recent_commits(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    days: int = 30,
    limit: int = DEFAULT_LIMIT,
) -> list[CommitResponse]:
    """Tool implementation: recent commits on the default branch."""
    return await guarded_tool_call(
        lambda: fetch_recent_commits(client, owner, repo, days=days, limit=limit),
        tool="get_recent_commits",
        owner=owner,
        repo=repo,
        not_found_message=f"Repository '{owner}/{repo}' was not found or is inaccessible.",
    )


def register_commit_tools(server: MCPServer, client: GitHubClient) -> None:
    """Register commit-related tools on the MCP server."""

    @server.tool(
        name="get_recent_commits",
        title="Get Recent Commits",
        description=(
            "List a repository's recent commits from the last N days (1-365), "
            "with SHA, message, author/committer, timestamps, and links."
        ),
    )
    async def _get_recent_commits(
        owner: OwnerParam,
        repo: RepoParam,
        days: DaysParam = 30,
        limit: LimitParam = DEFAULT_LIMIT,
    ) -> list[CommitResponse]:
        return await get_recent_commits(client, owner, repo, days=days, limit=limit)
