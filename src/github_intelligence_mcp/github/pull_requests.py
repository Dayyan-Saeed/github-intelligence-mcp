"""Pull request operations against the GitHub REST API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from github_intelligence_mcp.errors import ValidationError
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.payloads import (
    optional_login,
    parse_datetime,
    require_int,
    require_str,
)
from github_intelligence_mcp.models.pull_request import PullRequestResponse
from github_intelligence_mcp.utils.validation import validate_owner, validate_repo

PR_STATE_VALUES = frozenset({"open", "closed", "all"})
PR_SORT_VALUES = frozenset({"created", "updated", "popularity", "long-running"})
DIRECTION_VALUES = frozenset({"asc", "desc"})


async def get_pull_requests(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    state: str = "open",
    sort: str | None = None,
    direction: str = "desc",
    limit: int = 30,
) -> list[PullRequestResponse]:
    """Fetch up to ``limit`` pull requests for a repository."""
    owner = validate_owner(owner)
    repo = validate_repo(repo)
    if state not in PR_STATE_VALUES:
        raise ValidationError(f"state must be one of {sorted(PR_STATE_VALUES)}.", field="state")
    if sort is not None and sort not in PR_SORT_VALUES:
        raise ValidationError(
            f"sort must be one of {sorted(PR_SORT_VALUES)} or omitted.", field="sort"
        )
    if direction not in DIRECTION_VALUES:
        raise ValidationError(
            f"direction must be one of {sorted(DIRECTION_VALUES)}.", field="direction"
        )
    if not 1 <= limit <= 100:
        raise ValidationError("limit must be between 1 and 100.", field="limit")

    params: dict[str, Any] = {"state": state, "direction": direction}
    if sort is not None:
        params["sort"] = sort

    entries = await client.get_paginated(
        f"/repos/{owner}/{repo}/pulls", params=params, max_items=limit
    )
    return [build_pull_request_response(entry) for entry in entries]


def build_pull_request_response(entry: Mapping[str, Any]) -> PullRequestResponse:
    return PullRequestResponse(
        number=require_int(entry, "number"),
        title=require_str(entry, "title"),
        state=require_str(entry, "state"),
        author=optional_login(entry.get("user")),
        created_at=parse_datetime(require_str(entry, "created_at"), field="created_at"),
        updated_at=parse_datetime(require_str(entry, "updated_at"), field="updated_at"),
        closed_at=(
            parse_datetime(closed, field="closed_at")
            if (closed := entry.get("closed_at"))
            else None
        ),
        merged_at=(
            parse_datetime(merged, field="merged_at")
            if (merged := entry.get("merged_at"))
            else None
        ),
        draft=bool(entry.get("draft", False)),
        labels=_label_names(entry.get("labels")),
        html_url=require_str(entry, "html_url"),
    )


def _label_names(labels_payload: Any) -> list[str]:
    if not isinstance(labels_payload, list):
        return []
    names: list[str] = []
    for label in labels_payload:
        if isinstance(label, Mapping) and isinstance(name := label.get("name"), str):
            names.append(name)
    return names
