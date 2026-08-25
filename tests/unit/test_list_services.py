"""Tests for issue, pull-request, and commit service layers."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from github_intelligence_mcp.errors import ValidationError
from github_intelligence_mcp.github.commits import build_commit_response, get_recent_commits
from github_intelligence_mcp.github.issues import get_issues
from github_intelligence_mcp.github.pull_requests import get_pull_requests

FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"
BASE_URL = "https://api.github.test"


def _load(name: str) -> list[Any] | dict[str, Any]:
    value = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(value, (list, dict))
    return value


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_issues_filters_out_pull_requests(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/o/r/issues").mock(
        return_value=httpx.Response(200, json=_load("issues.json"))
    )

    issues = await get_issues(client, "o", "r", limit=10)

    assert [i.number for i in issues] == [14017]  # PR entry excluded


@respx.mock
async def test_get_issues_sends_labels_and_sort(client) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/repos/o/r/issues").mock(
        return_value=httpx.Response(200, json=[])
    )
    await get_issues(
        client, "o", "r", state="closed", labels=["bug", " react-dom "], sort="updated"
    )

    params = dict(route.calls.last.request.url.params)
    assert params["state"] == "closed"
    assert params["sort"] == "updated"
    assert params["labels"] == "bug,react-dom"


@pytest.mark.parametrize(
    ("kwargs", "field"),
    [
        ({"state": "weird"}, "state"),
        ({"sort": "drama"}, "sort"),
        ({"direction": "up"}, "direction"),
        ({"limit": 0}, "limit"),
        ({"labels": ["ok", ""]}, "labels"),
    ],
)
async def test_get_issues_rejects_invalid_input_before_http(  # type: ignore[no-untyped-def]
    client, kwargs: dict[str, Any], field: str
) -> None:
    with pytest.raises(ValidationError, match=field):
        await get_issues(client, "o", "r", **kwargs)


def test_issue_mapping_extracts_label_names() -> None:
    payload = _load("issues.json")
    assert isinstance(payload, list)
    issue = next(e for e in payload if "pull_request" not in e)

    from github_intelligence_mcp.github.issues import build_issue_response

    response = build_issue_response(issue)
    assert response.labels == ["bug", "react-dom"]
    assert response.author == "example-user"
    assert response.closed_at is None


# ---------------------------------------------------------------------------
# Pull requests
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_pull_requests_maps_fields(client) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE_URL}/repos/o/r/pulls").mock(
        return_value=httpx.Response(200, json=_load("pull_requests.json"))
    )

    pulls = await get_pull_requests(client, "o", "r", limit=10)

    assert len(pulls) == 2
    ready, draft = pulls
    assert ready.title.startswith("feat:")
    assert ready.draft is False
    assert ready.merged_at is None
    assert ready.labels == ["feature"]
    assert draft.draft is True


async def test_get_pull_requests_rejects_invalid_state(client) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValidationError, match="state"):
        await get_pull_requests(client, "o", "r", state="half-open")


# ---------------------------------------------------------------------------
# Commits
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_recent_commits_sends_since_window(client) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{BASE_URL}/repos/o/r/commits").mock(
        return_value=httpx.Response(200, json=_load("commits.json"))
    )

    commits = await get_recent_commits(client, "o", "r", days=7)

    since = str(route.calls.last.request.url.params["since"])
    assert since[:4].isdigit()
    assert len(commits) == 2


@pytest.mark.parametrize("bad_days", [0, -3, 366])
async def test_get_recent_commits_rejects_days_out_of_bounds(  # type: ignore[no-untyped-def]
    client, bad_days: int
) -> None:
    with pytest.raises(ValidationError, match="days"):
        await get_recent_commits(client, "o", "r", days=bad_days)


def test_commit_mapping_prefers_login_and_falls_back_to_name() -> None:
    first, second = _load("commits.json")
    assert isinstance(first, dict) and isinstance(second, dict)

    linked = build_commit_response(first)
    assert linked.author == "acdlite"  # GitHub login preferred
    assert linked.committer == "GitHub"  # falls back to git committer name

    unlinked = build_commit_response(second)
    assert unlinked.author == "Jane Doe"  # no linked account: raw git name
    assert unlinked.sha.startswith("aabbccdd")
