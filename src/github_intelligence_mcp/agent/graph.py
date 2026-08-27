"""Autonomous repository investigation graph.

Builds a LangGraph StateGraph that orchestrates MCP tool calls into a
complete repository investigation. The graph fetches metadata, computes
health scores, detects risks, gathers recent activity, and produces a
structured report — all without human intervention.

Usage::

    from github_intelligence_mcp.agent.graph import build_investigation_graph
    from github_intelligence_mcp.github.client import GitHubClient

    graph = build_investigation_graph(client)
    result = await graph.ainvoke(InvestigationState(owner="octocat", repo="Hello-World"))
    print(result.report)
"""

from __future__ import annotations

import asyncio
from typing import Any

from langgraph.graph import END, StateGraph

from github_intelligence_mcp.agent import InvestigationState
from github_intelligence_mcp.agent.report import generate_report
from github_intelligence_mcp.github.client import GitHubClient


def _make_node(client: GitHubClient, name: str, fn: Any) -> Any:
    """Wrap an async function as a LangGraph node."""

    async def node(state: InvestigationState) -> dict[str, Any]:
        try:
            result: dict[str, Any] = await fn(client, state)
            return result
        except Exception as exc:
            return {
                "errors": [*state.errors, f"{name}: {exc}"],
                "completed_steps": state.completed_steps,
            }

    return node


async def _fetch_metadata(client: GitHubClient, state: InvestigationState) -> dict[str, Any]:
    from github_intelligence_mcp.github.repositories import get_repository

    metadata = await get_repository(client, state.owner, state.repo)
    return {
        "metadata": metadata,
        "completed_steps": [*state.completed_steps, "metadata"],
    }


async def _analyze_health(client: GitHubClient, state: InvestigationState) -> dict[str, Any]:
    from github_intelligence_mcp.analysis.analyzer import gather_snapshot
    from github_intelligence_mcp.analysis.health import build_health_response

    snapshot = await gather_snapshot(client, state.owner, state.repo)
    health = build_health_response(
        snapshot,
        stale_issue_days=client.stale_issue_days,
        stale_pr_days=client.stale_pr_days,
    )
    return {
        "health": health,
        "completed_steps": [*state.completed_steps, "health"],
    }


async def _detect_risks(client: GitHubClient, state: InvestigationState) -> dict[str, Any]:
    from github_intelligence_mcp.analysis.analyzer import gather_snapshot
    from github_intelligence_mcp.analysis.risks import (
        aggregate_risk_level,
        aggregate_risk_score,
        detect_risks,
    )
    from github_intelligence_mcp.models.health import MaintenanceRiskResponse

    snapshot = await gather_snapshot(client, state.owner, state.repo)
    risks = detect_risks(
        snapshot,
        stale_issue_days=client.stale_issue_days,
        stale_pr_days=client.stale_pr_days,
    )
    risk_report = MaintenanceRiskResponse(
        owner=state.owner,
        repo=state.repo,
        risk_level=aggregate_risk_level(risks),
        risk_score=aggregate_risk_score(risks),
        risks=risks,
        computed_at=snapshot.now,
    )
    return {
        "risks": risk_report,
        "completed_steps": [*state.completed_steps, "risks"],
    }


async def _fetch_activity(client: GitHubClient, state: InvestigationState) -> dict[str, Any]:
    from github_intelligence_mcp.github.commits import get_recent_commits
    from github_intelligence_mcp.github.issues import get_issues
    from github_intelligence_mcp.github.pull_requests import get_pull_requests

    commits, issues, pulls = await asyncio.gather(
        get_recent_commits(client, state.owner, state.repo, limit=20),
        get_issues(client, state.owner, state.repo, state="open", limit=10),
        get_pull_requests(client, state.owner, state.repo, state="open", limit=10),
    )
    return {
        "recent_commits": commits,
        "open_issues": issues,
        "open_pulls": pulls,
        "completed_steps": [*state.completed_steps, "activity"],
    }


async def _generate_report_node(client: GitHubClient, state: InvestigationState) -> dict[str, Any]:
    report = generate_report(state)
    return {
        "report": report,
        "completed_steps": [*state.completed_steps, "report"],
    }


def build_investigation_graph(client: GitHubClient) -> Any:
    """Build and compile the investigation graph.

    Returns a compiled LangGraph graph ready for ``ainvoke``.
    """
    graph = StateGraph(InvestigationState)

    graph.add_node("fetch_metadata", _make_node(client, "fetch_metadata", _fetch_metadata))
    graph.add_node("analyze_health", _make_node(client, "analyze_health", _analyze_health))
    graph.add_node("detect_risks", _make_node(client, "detect_risks", _detect_risks))
    graph.add_node("fetch_activity", _make_node(client, "fetch_activity", _fetch_activity))
    graph.add_node("generate_report", _make_node(client, "generate_report", _generate_report_node))

    graph.set_entry_point("fetch_metadata")
    graph.add_edge("fetch_metadata", "analyze_health")
    graph.add_edge("analyze_health", "detect_risks")
    graph.add_edge("detect_risks", "fetch_activity")
    graph.add_edge("fetch_activity", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()
