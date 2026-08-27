"""Asynchronous client for the GitHub REST API.

This module is MCP-agnostic: it knows nothing about tools, resources, or
prompts. The MCP layer depends on this client; this client depends only on
httpx and application settings. It is deliberately structured so a GraphQL
transport can be added later without changing call sites.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import TracebackType
from typing import Any

import httpx

from github_intelligence_mcp import __version__
from github_intelligence_mcp.cache import Cache, NullCache
from github_intelligence_mcp.config import Settings
from github_intelligence_mcp.errors import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
)
from github_intelligence_mcp.logging import get_logger

_API_VERSION = "2022-11-28"
_MAX_ATTEMPTS = 3
_DEFAULT_BACKOFF_BASE_SECONDS = 0.5
_BACKOFF_CAP_SECONDS = 4.0
_DEFAULT_PER_PAGE = 50
_DEFAULT_MAX_SCAN = 250
_RATE_LIMIT_STATUSES = frozenset({403, 429})


@dataclass(frozen=True)
class RateLimitInfo:
    """Latest rate-limit state observed from GitHub response headers."""

    limit: int | None = None
    remaining: int | None = None
    reset_at: datetime | None = None


class GitHubClient:
    """Reusable asynchronous GitHub REST API client.

    One instance performs all HTTP traffic for the server; it must not be
    created per request. Transient failures (5xx, network errors) are retried
    with bounded exponential backoff; 4xx responses are never retried.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        backoff_base_seconds: float = _DEFAULT_BACKOFF_BASE_SECONDS,
        cache: Cache | None = None,
    ) -> None:
        self._settings = settings
        self._backoff_base_seconds = backoff_base_seconds
        self._cache = cache or NullCache()
        self._rate_limit = RateLimitInfo()
        self._log = get_logger("github.client")
        self._http = httpx.AsyncClient(
            base_url=settings.github_api_url,
            headers={
                # SecretStr keeps the token out of logs/reprs; only this
                # header construction ever touches the raw value.
                "Authorization": f"Bearer {settings.github_token.get_secret_value()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": _API_VERSION,
                "User-Agent": f"github-intelligence-mcp/{__version__}",
            },
            timeout=httpx.Timeout(settings.request_timeout_seconds),
        )

    @property
    def rate_limit(self) -> RateLimitInfo:
        """Most recent rate-limit information observed from GitHub."""
        return self._rate_limit

    @property
    def stale_issue_days(self) -> int:
        """Configured staleness threshold for issues."""
        return self._settings.stale_issue_days

    @property
    def stale_pr_days(self) -> int:
        """Configured staleness threshold for pull requests."""
        return self._settings.stale_pr_days

    async def get_json(self, path: str, *, params: Mapping[str, Any] | None = None) -> Any:
        """Perform a GET request and return the decoded JSON body."""
        cache_key = self._cache_key(path, params)
        ttl = self._ttl_for_path(path)
        if ttl > 0:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._log.debug("cache_hit path=%s", path)
                return cached
        response = await self._send(path, params=params)
        data = response.json()
        if ttl > 0:
            self._cache.set(cache_key, data, ttl)
        return data

    async def get_paginated(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        max_items: int,
        per_page: int = _DEFAULT_PER_PAGE,
        keep: Callable[[Any], bool] | None = None,
        max_scan: int = _DEFAULT_MAX_SCAN,
    ) -> list[Any]:
        """Fetch up to ``max_items`` entries from a list endpoint.

        Pagination is bounded by ``max_items`` (callers cap this at 100), so
        unbounded data fetching is impossible by construction.

        When ``keep`` is provided (e.g. to filter PRs out of the issues
        endpoint), only matching entries count toward ``max_items`` and raw
        scanning is additionally capped at ``max_scan`` entries so filtered
        endpoints can never trigger unbounded paging.
        """
        collected: list[Any] = []
        base_query: dict[str, Any] = dict(params or {})
        scanned = 0
        page = 1
        while len(collected) < max_items and scanned < max_scan:
            if keep is None:
                page_size = min(per_page, max_items - len(collected))
            else:
                page_size = min(per_page, max_scan - scanned)
            query = {**base_query, "page": page, "per_page": page_size}
            batch = await self.get_json(path, params=query)
            if not isinstance(batch, list):
                raise GitHubAPIError(f"Expected a list response from '{path}'.")
            scanned += len(batch)
            collected.extend(item for item in batch if keep is None or keep(item))
            if len(batch) < page_size:
                break
            page += 1
        return collected[:max_items]

    async def aclose(self) -> None:
        """Release the underlying HTTP connection pool."""
        await self._http.aclose()
        if hasattr(self._cache, "close"):
            self._cache.close()

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    @staticmethod
    def _cache_key(path: str, params: Mapping[str, Any] | None) -> str:
        """Build a cache key from the request path and params."""
        if not params:
            return path
        sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{path}?{sorted_params}"

    @staticmethod
    def _ttl_for_path(path: str) -> int:
        """Determine cache TTL based on the API endpoint path.

        Returns 0 to disable caching for unknown or non-cacheable endpoints.
        """
        if "/repos/" not in path:
            return 0
        if "/issues" in path and "/pulls" not in path:
            return 300  # 5 minutes
        if "/pulls" in path:
            return 300  # 5 minutes
        if "/commits" in path:
            return 120  # 2 minutes
        if "/contributors" in path:
            return 600  # 10 minutes
        if "/releases" in path:
            return 600  # 10 minutes
        return 600  # repository metadata: 10 minutes

    async def _send(self, path: str, *, params: Mapping[str, Any] | None) -> httpx.Response:
        delay = self._backoff_base_seconds
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = await self._http.get(path, params=params)
            except httpx.TransportError as exc:
                if attempt == _MAX_ATTEMPTS:
                    raise GitHubAPIError(
                        "Could not reach the GitHub API after several attempts."
                    ) from exc
                self._log.warning(
                    "transport_error path=%s attempt=%d error_type=%s",
                    path,
                    attempt,
                    type(exc).__name__,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, _BACKOFF_CAP_SECONDS)
                continue

            self._capture_rate_limit(response)
            if response.status_code >= 500 and attempt < _MAX_ATTEMPTS:
                self._log.warning(
                    "server_error path=%s status=%d attempt=%d",
                    path,
                    response.status_code,
                    attempt,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, _BACKOFF_CAP_SECONDS)
                continue

            self._raise_for_status(response)
            return response
        raise AssertionError("retry loop must exit via return or raise")  # pragma: no cover

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Map error responses onto domain exceptions with user-safe messages."""
        if response.is_success:
            return
        status = response.status_code
        detail = _extract_github_message(response)
        self._log.info("api_error status=%d detail=%s", status, detail)

        if status == 401:
            raise GitHubAuthenticationError()
        if status in _RATE_LIMIT_STATUSES and response.headers.get("x-ratelimit-remaining") == "0":
            raise GitHubRateLimitError(reset_at=self._rate_limit.reset_at)
        if status == 403:
            raise GitHubPermissionError()
        if status == 404:
            raise GitHubNotFoundError()
        raise GitHubAPIError(f"GitHub API request failed with status {status}.", status_code=status)

    def _capture_rate_limit(self, response: httpx.Response) -> None:
        headers = response.headers
        limit = _parse_optional_int(headers.get("x-ratelimit-limit"))
        remaining = _parse_optional_int(headers.get("x-ratelimit-remaining"))
        reset_epoch = _parse_optional_int(headers.get("x-ratelimit-reset"))
        reset_at = datetime.fromtimestamp(reset_epoch, tz=UTC) if reset_epoch is not None else None
        if limit is not None or remaining is not None or reset_at is not None:
            self._rate_limit = RateLimitInfo(limit=limit, remaining=remaining, reset_at=reset_at)
            self._log.debug("rate_limit remaining=%s limit=%s", remaining, limit)


def _extract_github_message(response: httpx.Response) -> str:
    """Best-effort extraction of GitHub's human-readable error message."""
    try:
        payload = response.json()
    except ValueError:
        return ""
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str):
            return message
    return ""


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
