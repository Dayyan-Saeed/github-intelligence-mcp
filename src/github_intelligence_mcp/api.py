"""REST API wrapper for MCP tools.

Provides HTTP endpoints that call our existing tool functions and return
JSON. This enables the Next.js dashboard to fetch data without subprocess
overhead or MCP protocol negotiation.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from github_intelligence_mcp.agent import InvestigationState
from github_intelligence_mcp.agent.graph import build_investigation_graph
from github_intelligence_mcp.analysis.analyzer import gather_snapshot
from github_intelligence_mcp.analysis.health import build_health_response
from github_intelligence_mcp.analysis.risks import (
    aggregate_risk_level,
    aggregate_risk_score,
    detect_risks,
)
from github_intelligence_mcp.config import load_settings
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.commits import get_recent_commits
from github_intelligence_mcp.github.contributors import get_contributors
from github_intelligence_mcp.github.issues import get_issues
from github_intelligence_mcp.github.pull_requests import get_pull_requests
from github_intelligence_mcp.github.releases import get_releases
from github_intelligence_mcp.github.repositories import get_repository
from github_intelligence_mcp.models.health import MaintenanceRiskResponse

_client: GitHubClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _client
    settings = load_settings()
    _client = GitHubClient(settings)
    yield
    if _client:
        await _client.aclose()


app = FastAPI(title="GitHub Intelligence API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_client() -> GitHubClient:
    if _client is None:
        raise HTTPException(status_code=503, detail="API not initialized")
    return _client


class RepoParam(BaseModel):
    owner: str
    repo: str


class CompareParam(BaseModel):
    owner_a: str
    repo_a: str
    owner_b: str
    repo_b: str


@app.get("/api/repository/{owner}/{repo}")
async def api_get_repository(owner: str, repo: str) -> dict[str, object]:
    client = _get_client()
    result = await get_repository(client, owner, repo)
    return result.model_dump(mode="json")


@app.get("/api/repository/{owner}/{repo}/health")
async def api_analyze_repository(owner: str, repo: str) -> dict[str, object]:
    client = _get_client()
    snapshot = await gather_snapshot(client, owner, repo)
    health = build_health_response(
        snapshot,
        stale_issue_days=client.stale_issue_days,
        stale_pr_days=client.stale_pr_days,
    )
    return health.model_dump(mode="json")


@app.get("/api/repository/{owner}/{repo}/risks")
async def api_find_risks(owner: str, repo: str) -> dict[str, object]:
    client = _get_client()
    snapshot = await gather_snapshot(client, owner, repo)
    risks = detect_risks(
        snapshot,
        stale_issue_days=client.stale_issue_days,
        stale_pr_days=client.stale_pr_days,
    )
    report = MaintenanceRiskResponse(
        owner=owner,
        repo=repo,
        risk_level=aggregate_risk_level(risks),
        risk_score=aggregate_risk_score(risks),
        risks=risks,
        computed_at=snapshot.now,
    )
    return report.model_dump(mode="json")


@app.get("/api/repository/{owner}/{repo}/commits")
async def api_get_commits(owner: str, repo: str) -> list[dict[str, object]]:
    client = _get_client()
    result = await get_recent_commits(client, owner, repo, limit=20)
    return [c.model_dump(mode="json") for c in result]


@app.get("/api/repository/{owner}/{repo}/issues")
async def api_get_issues(owner: str, repo: str) -> list[dict[str, object]]:
    client = _get_client()
    result = await get_issues(client, owner, repo, state="open", limit=10)
    return [i.model_dump(mode="json") for i in result]


@app.get("/api/repository/{owner}/{repo}/pulls")
async def api_get_pulls(owner: str, repo: str) -> list[dict[str, object]]:
    client = _get_client()
    result = await get_pull_requests(client, owner, repo, state="open", limit=10)
    return [p.model_dump(mode="json") for p in result]


@app.get("/api/repository/{owner}/{repo}/contributors")
async def api_get_contributors(owner: str, repo: str) -> list[dict[str, object]]:
    client = _get_client()
    result = await get_contributors(client, owner, repo, limit=10)
    return [c.model_dump(mode="json") for c in result]


@app.get("/api/repository/{owner}/{repo}/releases")
async def api_get_releases(owner: str, repo: str) -> list[dict[str, object]]:
    client = _get_client()
    result = await get_releases(client, owner, repo, limit=10)
    return [r.model_dump(mode="json") for r in result]


@app.get("/api/repository/{owner}/{repo}/investigate")
async def api_investigate(owner: str, repo: str) -> dict[str, object]:
    """Run the full autonomous investigation and return state + report."""
    client = _get_client()
    graph = build_investigation_graph(client)
    state = InvestigationState(owner=owner, repo=repo)
    result = await graph.ainvoke(state)
    if isinstance(result, dict):
        return {
            "owner": result.get("owner", owner),
            "repo": result.get("repo", repo),
            "health": result["health"].model_dump(mode="json") if result.get("health") else None,
            "risks": result["risks"].model_dump(mode="json") if result.get("risks") else None,
            "recent_commits": [c.model_dump(mode="json") for c in result.get("recent_commits", [])],
            "open_issues": [i.model_dump(mode="json") for i in result.get("open_issues", [])],
            "open_pulls": [p.model_dump(mode="json") for p in result.get("open_pulls", [])],
            "report": result.get("report", ""),
            "errors": result.get("errors", []),
            "completed_steps": result.get("completed_steps", []),
        }
    return {
        "owner": result.owner,
        "repo": result.repo,
        "health": result.health.model_dump(mode="json") if result.health else None,
        "risks": result.risks.model_dump(mode="json") if result.risks else None,
        "recent_commits": [c.model_dump(mode="json") for c in result.recent_commits],
        "open_issues": [i.model_dump(mode="json") for i in result.open_issues],
        "open_pulls": [p.model_dump(mode="json") for p in result.open_pulls],
        "report": result.report,
        "errors": result.errors,
        "completed_steps": result.completed_steps,
    }


@app.get("/api/compare/{owner_a}/{repo_a}/{owner_b}/{repo_b}")
async def api_compare(owner_a: str, repo_a: str, owner_b: str, repo_b: str) -> dict[str, object]:
    from github_intelligence_mcp.analysis.comparison import compare_snapshots

    client = _get_client()
    import asyncio

    snap_a, snap_b = await asyncio.gather(
        gather_snapshot(client, owner_a, repo_a),
        gather_snapshot(client, owner_b, repo_b),
    )
    health_a = build_health_response(
        snap_a,
        stale_issue_days=client.stale_issue_days,
        stale_pr_days=client.stale_pr_days,
    )
    health_b = build_health_response(
        snap_b,
        stale_issue_days=client.stale_issue_days,
        stale_pr_days=client.stale_pr_days,
    )
    comparison = compare_snapshots(snap_a, snap_b, health_a, health_b)
    return comparison.model_dump(mode="json")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
