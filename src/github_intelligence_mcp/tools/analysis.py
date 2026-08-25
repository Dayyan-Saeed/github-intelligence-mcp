"""MCP tools for repository analysis (Phase 2)."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from github_intelligence_mcp.analysis.analyzer import analyze_repository as run_analysis
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.models.health import RepositoryHealthResponse
from github_intelligence_mcp.tools._guard import guarded_tool_call
from github_intelligence_mcp.tools.parameters import OwnerParam, RepoParam


async def analyze_repository(
    client: GitHubClient, owner: str, repo: str
) -> RepositoryHealthResponse:
    """Tool implementation: deterministic multi-component health assessment."""
    return await guarded_tool_call(
        lambda: run_analysis(
            client,
            owner,
            repo,
            stale_issue_days=client.stale_issue_days,
            stale_pr_days=client.stale_pr_days,
        ),
        tool="analyze_repository",
        owner=owner,
        repo=repo,
        not_found_message=f"Repository '{owner}/{repo}' was not found or is inaccessible.",
    )


def register_analysis_tools(server: MCPServer, client: GitHubClient) -> None:
    """Register analysis-related tools on the MCP server."""

    @server.tool(
        name="analyze_repository",
        title="Analyze Repository",
        description=(
            "Compute a deterministic health assessment for a GitHub repository: "
            "activity, issue health, pull-request health, contributor health, "
            "release activity, and documentation — each scored 0-100 with "
            "evidence, plus a weighted overall score and letter grade. "
            "Read-only; no AI judgement involved."
        ),
    )
    async def _analyze_repository(owner: OwnerParam, repo: RepoParam) -> RepositoryHealthResponse:
        return await analyze_repository(client, owner, repo)
