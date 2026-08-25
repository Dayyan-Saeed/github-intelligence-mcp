"""Public MCP response models.

These models define the stable, structured output contract of MCP tools.
They are intentionally decoupled from raw GitHub API payload shapes; the
``github`` package maps payloads onto them so tool schemas never shift when
GitHub changes its API responses.
"""

from github_intelligence_mcp.models.repository import RepositoryResponse, RepositorySummary

__all__ = [
    "RepositoryResponse",
    "RepositorySummary",
]
