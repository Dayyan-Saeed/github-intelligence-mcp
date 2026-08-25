"""MCP tools for issue data."""

from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.issues import get_issues as fetch_issues
from github_intelligence_mcp.models.issue import IssueResponse
from github_intelligence_mcp.tools._guard import guarded_tool_call
from github_intelligence_mcp.tools.parameters import (
    DEFAULT_LIMIT,
    LimitParam,
    OwnerParam,
    RepoParam,
)

IssueStateParam = Literal["open", "closed", "all"]
IssueSortParam = Literal["created", "updated", "comments"]
DirectionParam = Literal["asc", "desc"]

LabelsParam = Annotated[
    list[str] | None,
    Field(default=None, description="Filter issues by these label names.", max_length=20),
]


async def get_issues(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    state: str = "open",
    labels: list[str] | None = None,
    sort: str | None = None,
    direction: str = "desc",
    limit: int = DEFAULT_LIMIT,
) -> list[IssueResponse]:
    """Tool implementation: issues of a repository (PRs excluded)."""
    return await guarded_tool_call(
        lambda: fetch_issues(
            client,
            owner,
            repo,
            state=state,
            labels=labels,
            sort=sort,
            direction=direction,
            limit=limit,
        ),
        tool="get_issues",
        owner=owner,
        repo=repo,
        not_found_message=f"Repository '{owner}/{repo}' was not found or is inaccessible.",
    )


def register_issue_tools(server: MCPServer, client: GitHubClient) -> None:
    """Register issue-related tools on the MCP server."""

    @server.tool(
        name="get_issues",
        title="Get Issues",
        description=(
            "List a repository's issues with number, title, state, author, "
            "timestamps, and labels. Pull requests are automatically excluded."
        ),
    )
    async def _get_issues(
        owner: OwnerParam,
        repo: RepoParam,
        state: IssueStateParam = "open",
        labels: LabelsParam = None,
        sort: IssueSortParam | None = None,
        direction: DirectionParam = "desc",
        limit: LimitParam = DEFAULT_LIMIT,
    ) -> list[IssueResponse]:
        return await get_issues(
            client,
            owner,
            repo,
            state=state,
            labels=labels,
            sort=sort,
            direction=direction,
            limit=limit,
        )
