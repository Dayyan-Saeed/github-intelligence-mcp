"""Shared helpers for mapping raw GitHub API payloads onto response models.

Every helper raises :class:`GitHubAPIError` with a user-safe message when the
payload violates expectations, so malformed upstream data never surfaces as a
crash to MCP clients.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from github_intelligence_mcp.errors import GitHubAPIError


def require_str(payload: Mapping[str, Any], key: str) -> str:
    value = require(payload, key)
    if not isinstance(value, str):
        raise GitHubAPIError(f"Unexpected GitHub API payload: '{key}' is not a string.")
    return value


def require_int(payload: Mapping[str, Any], key: str) -> int:
    value = require(payload, key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise GitHubAPIError(f"Unexpected GitHub API payload: '{key}' is not an integer.")
    return value


def parse_datetime(value: str, *, field: str) -> datetime:
    """Parse an ISO-8601 GitHub timestamp (``...Z`` suffix tolerated)."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GitHubAPIError(
            f"Unexpected GitHub API payload: '{field}' is not a valid timestamp."
        ) from exc


def optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def optional_login(author: Any) -> str | None:
    """Extract ``login`` from an embedded user object when present."""
    if isinstance(author, Mapping):
        login = author.get("login")
        return login if isinstance(login, str) else None
    return None


def require(payload: Mapping[str, Any], key: str) -> Any:
    try:
        return payload[key]
    except KeyError as exc:
        raise GitHubAPIError(f"Unexpected GitHub API payload: missing '{key}'.") from exc
