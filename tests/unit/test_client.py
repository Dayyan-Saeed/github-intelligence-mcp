"""Tests for the GitHub API client: auth, error mapping, retries, pagination."""

from datetime import UTC, datetime

import httpx
import pytest
import respx

from github_intelligence_mcp.errors import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
)
from github_intelligence_mcp.github.client import _MAX_ATTEMPTS

BASE_URL = "https://api.github.test"


@respx.mock
async def test_request_sends_auth_and_api_headers(client) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/repos/a/b").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    data = await client.get_json("/repos/a/b")

    assert data == {"ok": True}
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer test-token-value"
    assert request.headers["Accept"] == "application/vnd.github+json"
    assert request.headers["X-GitHub-Api-Version"] == "2022-11-28"
    assert "github-intelligence-mcp/" in request.headers["User-Agent"]


@respx.mock
async def test_unauthorized_maps_to_auth_error(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/a/b").mock(
        return_value=httpx.Response(401, json={"message": "Bad credentials"})
    )
    with pytest.raises(GitHubAuthenticationError):
        await client.get_json("/repos/a/b")


@respx.mock
async def test_not_found_maps_to_not_found_error(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/a/b").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    with pytest.raises(GitHubNotFoundError, match="not found or is inaccessible"):
        await client.get_json("/repos/a/b")


@respx.mock
async def test_rate_limited_response_raises_rate_limit_error(client) -> None:  # type: ignore[no-untyped-def]
    reset_epoch = 1790000000
    respx.get(f"{BASE_URL}/repos/a/b").mock(
        return_value=httpx.Response(
            403,
            headers={
                "x-ratelimit-remaining": "0",
                "x-ratelimit-limit": "5000",
                "x-ratelimit-reset": str(reset_epoch),
            },
            json={"message": "API rate limit exceeded"},
        )
    )
    with pytest.raises(GitHubRateLimitError) as excinfo:
        await client.get_json("/repos/a/b")
    assert excinfo.value.reset_at == datetime.fromtimestamp(reset_epoch, tz=UTC)
    assert "rate limit" in str(excinfo.value).lower()


@respx.mock
async def test_plain_forbidden_maps_to_permission_error(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/a/b").mock(
        return_value=httpx.Response(403, json={"message": "Forbidden"})
    )
    with pytest.raises(GitHubPermissionError):
        await client.get_json("/repos/a/b")


@respx.mock
async def test_429_with_exhausted_limit_maps_to_rate_limit_error(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/a/b").mock(
        return_value=httpx.Response(
            429,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1790000000"},
        )
    )
    with pytest.raises(GitHubRateLimitError):
        await client.get_json("/repos/a/b")


@respx.mock
async def test_server_error_is_retried_then_succeeds(client) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/repos/a/b").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, json={"ok": 1}),
        ]
    )
    data = await client.get_json("/repos/a/b")
    assert data == {"ok": 1}
    assert route.call_count == 2


@respx.mock
async def test_persistent_server_error_raises_after_bounded_attempts(client) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/repos/a/b").mock(return_value=httpx.Response(503))
    with pytest.raises(GitHubAPIError):
        await client.get_json("/repos/a/b")
    assert route.call_count == _MAX_ATTEMPTS


@respx.mock
async def test_transport_errors_are_retried_with_bound(client) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/repos/a/b").mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(GitHubAPIError, match="Could not reach") as excinfo:
        await client.get_json("/repos/a/b")
    assert isinstance(excinfo.value.__cause__, httpx.TransportError)
    assert route.call_count == _MAX_ATTEMPTS


@respx.mock
async def test_client_errors_are_never_retried(client) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/repos/a/b").mock(return_value=httpx.Response(422))
    with pytest.raises(GitHubAPIError, match="422"):
        await client.get_json("/repos/a/b")
    assert route.call_count == 1


@respx.mock
async def test_rate_limit_info_captured_from_headers(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/a/b").mock(
        return_value=httpx.Response(
            200,
            headers={
                "x-ratelimit-limit": "5000",
                "x-ratelimit-remaining": "4999",
                "x-ratelimit-reset": "1790000000",
            },
            json={},
        )
    )
    await client.get_json("/repos/a/b")
    assert client.rate_limit.limit == 5000
    assert client.rate_limit.remaining == 4999
    assert client.rate_limit.reset_at is not None


@respx.mock
async def test_pagination_stops_on_short_page(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/o/r/issues").mock(
        side_effect=[
            httpx.Response(200, json=list(range(50))),
            httpx.Response(200, json=list(range(50, 80))),
        ]
    )
    items = await client.get_paginated("/repos/o/r/issues", max_items=100)
    assert items == list(range(80))


@respx.mock
async def test_pagination_truncates_and_caps_page_size(client) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/repos/o/r/issues").mock(
        side_effect=[
            httpx.Response(200, json=list(range(50))),
            httpx.Response(200, json=list(range(50, 100))),
            httpx.Response(200, json=list(range(100, 150))),
        ]
    )
    items = await client.get_paginated("/repos/o/r/issues", max_items=120)
    assert len(items) == 120

    last_params = dict(route.calls.last.request.url.params)
    assert last_params["page"] == "3"
    # Only 20 items remained of the 120 budget; page size must shrink.
    assert last_params["per_page"] == "20"


@respx.mock
async def test_pagination_rejects_non_list_payload(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/o/r/issues").mock(
        return_value=httpx.Response(200, json={"unexpected": True})
    )
    with pytest.raises(GitHubAPIError, match="list"):
        await client.get_paginated("/repos/o/r/issues", max_items=10)
