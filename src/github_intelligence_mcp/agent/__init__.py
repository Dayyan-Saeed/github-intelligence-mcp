"""Investigation agent state.

Defines the shared state that flows through the LangGraph investigation
graph. Each node reads from and writes to this state, building up the
investigation result incrementally.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from github_intelligence_mcp.models.commit import CommitResponse
from github_intelligence_mcp.models.health import (
    MaintenanceRiskResponse,
    RepositoryHealthResponse,
)
from github_intelligence_mcp.models.issue import IssueResponse
from github_intelligence_mcp.models.pull_request import PullRequestResponse
from github_intelligence_mcp.models.repository import RepositoryResponse


@dataclass
class InvestigationState:
    """Mutable state shared across all investigation nodes."""

    owner: str
    repo: str

    # Filled by nodes
    metadata: RepositoryResponse | None = None
    health: RepositoryHealthResponse | None = None
    risks: MaintenanceRiskResponse | None = None
    recent_commits: list[CommitResponse] = field(default_factory=list)
    open_issues: list[IssueResponse] = field(default_factory=list)
    open_pulls: list[PullRequestResponse] = field(default_factory=list)
    report: str = ""

    # Error tracking
    errors: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
