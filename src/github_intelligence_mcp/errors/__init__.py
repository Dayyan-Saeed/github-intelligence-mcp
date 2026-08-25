"""Domain exceptions for GitHub Intelligence MCP."""

from github_intelligence_mcp.errors.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubIntelligenceError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
    ValidationError,
)

__all__ = [
    "GitHubAPIError",
    "GitHubAuthenticationError",
    "GitHubIntelligenceError",
    "GitHubNotFoundError",
    "GitHubPermissionError",
    "GitHubRateLimitError",
    "ValidationError",
]
