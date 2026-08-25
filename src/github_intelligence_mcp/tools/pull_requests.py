"""MCP tools for pull request data."""

from __future__ import annotations

from typing import Literal

from mcp.server.mcpserver import MCPServer

from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.pull_requests import (
    get_pull_requests as fetch_pull_requests,
)
from github_intelligence_mcp.models.pull_request import PullRequestResponse
from github_intelligence_mcp.tools._guard import guarded_tool_call
from github_intelligence_mcp.tools.parameters import (
    DEFAULT_LIMIT,
    LimitParam,
    OwnerParam,
    RepoParam,
)

PullRequestStateParam = Literal["open", "closed", "all"]
PullRequestSortParam = Literal["created", "updated", "popularity", "long-running"]
DirectionParam = Literal["asc", "desc"]


async def get_pull_requests(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    state: str = "open",
    sort: str | None = None,
    direction: str = "desc",
    limit: int = DEFAULT_LIMIT,
) -> list[PullRequestResponse]:
    """Tool implementation: pull requests of a repository."""
    return await guarded_tool_call(
        lambda: fetch_pull_requests(
            client, owner, repo, state=state, sort=sort, direction=direction, limit=limit
        ),
        tool="get_pull_requests",
        owner=owner,
        repo=repo,
        not_found_message=f"Repository '{owner}/{repo}' was not found or is inaccessible.",
    )


def register_pull_request_tools(server: MCPServer, client: GitHubClient) -> None:
    """Register pull-request-related tools on the MCP server."""

    @server.tool(
        name="get_pull_requests",
        title="Get Pull Requests",
        description=(
            "List a repository's pull requests with number, title, state, "
            "author, created/updated/closed/merged timestamps, draft flag, "
            "and labels."
        ),
    )
    async def _get_pull_requests(
        owner: OwnerParam,
        repo: RepoParam,
        state: PullRequestStateParam = "open",
        sort: PullRequestSortParam | None = None,
        direction: DirectionParam = "desc",
        limit: LimitParam = DEFAULT_LIMIT,
    ) -> list[PullRequestResponse]:
        return await get_pull_requests(
            client, owner, repo, state=state, sort=sort, direction=direction, limit=limit
        )
