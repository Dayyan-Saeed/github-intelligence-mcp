"""Domain exceptions.

Exception messages are written to be safe for end users: they never contain
credentials, URLs with tokens, or stack traces. The MCP layer converts these
into clean tool errors.
"""

from __future__ import annotations

from datetime import datetime

__all__ = [
    "GitHubAPIError",
    "GitHubAuthenticationError",
    "GitHubIntelligenceError",
    "GitHubNotFoundError",
    "GitHubPermissionError",
    "GitHubRateLimitError",
    "ValidationError",
]


class GitHubIntelligenceError(Exception):
    """Base class for all application errors."""


class ValidationError(GitHubIntelligenceError):
    """Raised when tool input fails validation.

    Deliberately distinct from :class:`pydantic.ValidationError`; this class
    represents invalid input arriving at a tool boundary.
    """

    def __init__(
        self,
        message: str = "The provided input is invalid.",
        *,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.field = field


class GitHubAPIError(GitHubIntelligenceError):
    """Base class for GitHub API failures."""

    def __init__(
        self,
        message: str = "The GitHub API request failed.",
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubAuthenticationError(GitHubAPIError):
    """Raised when GitHub rejects the configured credentials (HTTP 401)."""

    def __init__(
        self,
        message: str = "GitHub rejected the configured credentials. Check GITHUB_TOKEN.",
    ) -> None:
        super().__init__(message, status_code=401)


class GitHubNotFoundError(GitHubAPIError):
    """Raised when a resource does not exist or is inaccessible (HTTP 404)."""

    def __init__(
        self,
        message: str = "The requested resource was not found or is inaccessible.",
    ) -> None:
        super().__init__(message, status_code=404)


class GitHubPermissionError(GitHubAPIError):
    """Raised when the token lacks permission for the resource (HTTP 403)."""

    def __init__(
        self,
        message: str = "The configured token does not have permission to access this resource.",
    ) -> None:
        super().__init__(message, status_code=403)


class GitHubRateLimitError(GitHubAPIError):
    """Raised when the GitHub API rate limit is exhausted (HTTP 403/429)."""

    def __init__(
        self,
        message: str = (
            "GitHub API rate limit exceeded. Please retry after the provided reset time."
        ),
        *,
        status_code: int | None = None,
        reset_at: datetime | None = None,
    ) -> None:
        if reset_at is not None:
            formatted = reset_at.strftime("%Y-%m-%d %H:%M:%S %Z")
            message = f"{message} Reset at: {formatted}."
        super().__init__(message, status_code=status_code)
        self.reset_at = reset_at
