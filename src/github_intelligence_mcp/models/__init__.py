"""Public MCP response models.

These models define the stable, structured output contract of MCP tools.
They are intentionally decoupled from raw GitHub API payload shapes; the
``github`` package maps payloads onto them so tool schemas never shift when
GitHub changes its API responses.
"""

from github_intelligence_mcp.models.commit import CommitResponse
from github_intelligence_mcp.models.contributor import ContributorResponse
from github_intelligence_mcp.models.health import (
    ComparisonDimension,
    ComponentScore,
    MaintenanceRiskResponse,
    RepositoryComparisonResponse,
    RepositoryHealthResponse,
    RiskItem,
)
from github_intelligence_mcp.models.issue import IssueResponse
from github_intelligence_mcp.models.pull_request import PullRequestResponse
from github_intelligence_mcp.models.release import ReleaseResponse
from github_intelligence_mcp.models.repository import (
    RepositoryResponse,
    RepositorySummary,
    SearchRepositoriesResponse,
)

__all__ = [
    "CommitResponse",
    "ComparisonDimension",
    "ComponentScore",
    "ContributorResponse",
    "IssueResponse",
    "MaintenanceRiskResponse",
    "PullRequestResponse",
    "ReleaseResponse",
    "RepositoryComparisonResponse",
    "RepositoryHealthResponse",
    "RepositoryResponse",
    "RepositorySummary",
    "RiskItem",
    "SearchRepositoriesResponse",
]
