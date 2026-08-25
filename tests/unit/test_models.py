"""Tests for repository response model mapping."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from github_intelligence_mcp.errors import GitHubAPIError
from github_intelligence_mcp.github.repositories import build_repository_response

FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"


@pytest.fixture
def repository_payload() -> dict[str, Any]:
    raw = (FIXTURES_DIR / "repository.json").read_text(encoding="utf-8")
    return dict(json.loads(raw))


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


def test_response_model_is_immutable(repository_payload: dict[str, Any]) -> None:
    response = build_repository_response(repository_payload)
    with pytest.raises(ValueError, match=r"frozen|immutable"):
        response.stars = 1
