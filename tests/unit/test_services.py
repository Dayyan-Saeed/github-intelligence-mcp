"""Tests for GitHub service-layer functions (validation, filtering, pagination use)."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from github_intelligence_mcp.errors import ValidationError
from github_intelligence_mcp.github.contributors import get_contributors
from github_intelligence_mcp.github.releases import get_releases
from github_intelligence_mcp.github.repositories import search_repositories

FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"
BASE_URL = "https://api.github.test"


def _load(name: str) -> list[Any] | dict[str, Any]:
    value = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(value, (list, dict))
    return value


@respx.mock
async def test_search_rejects_invalid_sort_before_any_http(client) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/search/repositories")
    with pytest.raises(ValidationError, match="sort"):
        await search_repositories(client, "react", sort="cuteness")
    assert not route.called


@respx.mock
async def test_search_rejects_invalid_order_before_any_http(client) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/search/repositories")
    with pytest.raises(ValidationError, match="order"):
        await search_repositories(client, "react", order="sideways")
    assert not route.called


@respx.mock
async def test_search_rejects_out_of_range_limit_before_any_http(client) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/search/repositories")
    for bad_limit in (0, 101, -5):
        with pytest.raises(ValidationError, match="limit"):
            await search_repositories(client, "react", limit=bad_limit)
    assert not route.called


@respx.mock
async def test_search_sends_sort_only_when_provided(client) -> None:  # type: ignore[no-untyped-def]
    payload = _load("search_repositories.json")
    route = respx.get(f"{BASE_URL}/search/repositories").mock(
        return_value=httpx.Response(200, json=payload)
    )

    response = await search_repositories(client, "language:python", sort="stars", limit=2)

    params = dict(route.calls.last.request.url.params)
    assert params["sort"] == "stars"
    assert params["order"] == "desc"
    assert params["per_page"] == "2"
    assert response.total_count == 2


@respx.mock
async def test_contributors_skip_anonymous_entries(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/o/r/contributors").mock(
        return_value=httpx.Response(200, json=_load("contributors.json"))
    )

    contributors = await get_contributors(client, "o", "r", limit=10)

    usernames = [c.username for c in contributors]
    assert usernames == ["gaearon", "sophiebits"]  # anonymous entry skipped


@respx.mock
async def test_releases_respect_limit_bound(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/o/r/releases").mock(
        side_effect=[
            httpx.Response(200, json=_load("releases.json")),
            httpx.Response(200, json=[]),
        ]
    )

    releases = await get_releases(client, "o", "r", limit=100)

    assert len(releases) == 2
    assert releases[0].tag_name == "v19.1.0"
    assert releases[1].draft is True
