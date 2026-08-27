"""MCP tools for repository analysis (Phase 2)."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from github_intelligence_mcp.analysis.analyzer import analyze_repository as run_analysis
from github_intelligence_mcp.analysis.analyzer import gather_snapshot
from github_intelligence_mcp.analysis.risks import (
    aggregate_risk_level,
    aggregate_risk_score,
    detect_risks,
)
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.models.health import MaintenanceRiskResponse, RepositoryHealthResponse
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


async def find_maintenance_risks(
    client: GitHubClient, owner: str, repo: str
) -> MaintenanceRiskResponse:
    """Tool implementation: evidence-backed maintenance risk detection."""
    return await guarded_tool_call(
        lambda: _build_risk_report(client, owner, repo),
        tool="find_maintenance_risks",
        owner=owner,
        repo=repo,
        not_found_message=f"Repository '{owner}/{repo}' was not found or is inaccessible.",
    )


async def _build_risk_report(
    client: GitHubClient, owner: str, repo: str
) -> MaintenanceRiskResponse:
    snapshot = await gather_snapshot(client, owner, repo)
    risks = detect_risks(
        snapshot,
        stale_issue_days=client.stale_issue_days,
        stale_pr_days=client.stale_pr_days,
    )
    return MaintenanceRiskResponse(
        owner=snapshot.owner,
        repo=snapshot.repo,
        risk_level=aggregate_risk_level(risks),
        risk_score=aggregate_risk_score(risks),
        risks=risks,
        computed_at=snapshot.now,
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

    @server.tool(
        name="find_maintenance_risks",
        title="Find Maintenance Risks",
        description=(
            "Detect concrete maintenance risks in a GitHub repository — stale "
            "issues, stale pull requests, inactivity, bus factor, contributor "
            "concentration, release gaps — each with severity and supporting "
            "evidence."
        ),
    )
    async def _find_maintenance_risks(
        owner: OwnerParam, repo: RepoParam
    ) -> MaintenanceRiskResponse:
        return await find_maintenance_risks(client, owner, repo)
