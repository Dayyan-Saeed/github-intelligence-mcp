"""Tests for response model mapping across all domains."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from github_intelligence_mcp.errors import GitHubAPIError
from github_intelligence_mcp.github.contributors import build_contributor_response
from github_intelligence_mcp.github.releases import build_release_response
from github_intelligence_mcp.github.repositories import (
    build_repository_response,
    build_search_response,
)

FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"


def _load(name: str) -> Any:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def repository_payload() -> dict[str, Any]:
    return dict(_load("repository.json"))


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


def test_repository_mapping(repository_payload: dict[str, Any]) -> None:
    response = build_repository_response(repository_payload)

    assert response.name == "react"
    assert response.full_name == "facebook/react"
    assert response.description == "The library for web and native user interfaces."
    assert response.private is False
    assert response.fork is False
    assert response.stars == 238000
    assert response.forks == 49000
    assert response.watchers == 238000
    assert response.open_issues == 612
    assert response.language == "JavaScript"
    assert response.license == "MIT"
    assert response.default_branch == "main"
    assert response.created_at == datetime(2013, 5, 24, 16, 15, 54, tzinfo=UTC)
    assert response.pushed_at == datetime(2026, 8, 19, 18, 30, 0, tzinfo=UTC)
    assert response.html_url == "https://github.com/facebook/react"


def test_missing_license_maps_to_none(repository_payload: dict[str, Any]) -> None:
    repository_payload["license"] = None
    assert build_repository_response(repository_payload).license is None


def test_noassertion_license_maps_to_none(repository_payload: dict[str, Any]) -> None:
    repository_payload["license"] = {"spdx_id": "NOASSERTION", "name": "Other"}
    assert build_repository_response(repository_payload).license is None


def test_null_pushed_at_is_tolerated(repository_payload: dict[str, Any]) -> None:
    repository_payload["pushed_at"] = None
    assert build_repository_response(repository_payload).pushed_at is None


def test_missing_required_field_raises_clean_api_error(repository_payload: dict[str, Any]) -> None:
    del repository_payload["stargazers_count"]
    with pytest.raises(GitHubAPIError, match="stargazers_count"):
        build_repository_response(repository_payload)


def test_malformed_timestamp_raises_clean_api_error(repository_payload: dict[str, Any]) -> None:
    repository_payload["created_at"] = "not-a-date"
    with pytest.raises(GitHubAPIError, match="timestamp"):
        build_repository_response(repository_payload)


def test_response_model_is_immutable(repository_payload: dict[str, Any]) -> None:
    response = build_repository_response(repository_payload)
    with pytest.raises(ValueError, match=r"frozen|immutable"):
        response.stars = 1


# ---------------------------------------------------------------------------
# Repository search
# ---------------------------------------------------------------------------


def test_search_response_mapping() -> None:
    payload = _load("search_repositories.json")

    response = build_search_response(payload)

    assert response.total_count == 2
    assert response.incomplete_results is False
    assert len(response.items) == 2
    first = response.items[0]
    assert first.full_name == "facebook/react"
    assert first.stars == 238000
    second = response.items[1]
    assert second.full_name == "vuejs/vue"


def test_search_response_rejects_non_list_items() -> None:
    with pytest.raises(GitHubAPIError, match="items"):
        build_search_response({"total_count": 0, "items": "nope"})


# ---------------------------------------------------------------------------
# Contributors
# ---------------------------------------------------------------------------


def test_contributor_mapping() -> None:
    entry = {
        "login": "gaearon",
        "contributions": 1042,
        "avatar_url": "https://avatars.githubusercontent.com/u/810438?v=4",
        "html_url": "https://github.com/gaearon",
    }

    response = build_contributor_response(entry)

    assert response.username == "gaearon"
    assert response.contributions == 1042
    assert str(response.avatar_url).endswith("v=4")
    assert response.html_url == "https://github.com/gaearon"


# ---------------------------------------------------------------------------
# Releases
# ---------------------------------------------------------------------------


def test_release_mapping() -> None:
    release, draft = _load("releases.json")

    published = build_release_response(release)
    assert published.tag_name == "v19.1.0"
    assert published.name == "19.1.0"
    assert published.author == "react-bot"
    assert published.draft is False
    assert published.prerelease is False
    assert published.published_at == datetime(2026, 3, 20, 14, 30, 0, tzinfo=UTC)
    assert published.created_at == datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC)

    draft_response = build_release_response(draft)
    assert draft_response.tag_name == "v19.2.0-rc1"
    assert draft_response.name is None
    assert draft_response.author == "epicfaace"
    assert draft_response.draft is True
    assert draft_response.prerelease is True
    assert draft_response.published_at is None
