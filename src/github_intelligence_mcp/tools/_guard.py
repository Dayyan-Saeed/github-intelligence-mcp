"""Shared tool-boundary guard: timing, structured logging, error translation.

Every MCP tool implementation runs its domain operation through
:func:`guarded_tool_call`, which guarantees:

- consistent success/failure logs (tool name, repository, duration),
- domain exceptions become clean :class:`ToolError` messages,
- no raw exception text ever reaches MCP clients un-curated.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from mcp.server.mcpserver.exceptions import ToolError

from github_intelligence_mcp.errors import (
    GitHubIntelligenceError,
    GitHubNotFoundError,
    ValidationError,
)
from github_intelligence_mcp.logging import get_logger

_log = get_logger("tools.guard")

T = TypeVar("T")


async def guarded_tool_call(
    operation: Callable[[], Awaitable[T]],
    *,
    tool: str,
    owner: str | None = None,
    repo: str | None = None,
    not_found_message: str | None = None,
) -> T:
    """Run ``operation``, translating domain errors into user-safe tool errors."""
    started = time.perf_counter()
    try:
        result = await operation()
    except GitHubNotFoundError as exc:
        _log_failure(tool, owner, repo, "not_found", level="warning")
        message = not_found_message if not_found_message is not None else str(exc)
        raise ToolError(message) from exc
    except ValidationError as exc:
        _log_failure(tool, owner, repo, "invalid_input", level="info")
        raise ToolError(str(exc)) from exc
    except GitHubIntelligenceError as exc:
        _log_failure(tool, owner, repo, type(exc).__name__, level="warning")
        raise ToolError(str(exc)) from exc

    duration_ms = (time.perf_counter() - started) * 1000
    _log.info(
        "tool=%s owner=%s repo=%s status=success duration_ms=%.1f",
        tool,
        owner,
        repo,
        duration_ms,
    )
    return result


def _log_failure(
    tool: str,
    owner: str | None,
    repo: str | None,
    reason: str,
    *,
    level: str,
) -> None:
    message = "tool=%s owner=%s repo=%s status=error reason=%s"
    args: tuple[str | None, ...] = (tool, owner, repo, reason)
    if level == "warning":
        _log.warning(message, *args)
    else:
        _log.info(message, *args)
