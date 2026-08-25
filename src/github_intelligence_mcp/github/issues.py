"""Issue operations against the GitHub REST API."""

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
from github_intelligence_mcp.models.issue import IssueResponse
from github_intelligence_mcp.utils.validation import validate_owner, validate_repo

ISSUE_STATE_VALUES = frozenset({"open", "closed", "all"})
ISSUE_SORT_VALUES = frozenset({"created", "updated", "comments"})
DIRECTION_VALUES = frozenset({"asc", "desc"})


async def get_issues(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    state: str = "open",
    labels: list[str] | None = None,
    sort: str | None = None,
    direction: str = "desc",
    limit: int = 30,
) -> list[IssueResponse]:
    """Fetch up to ``limit`` issues for a repository.

    GitHub's issues endpoint also returns pull requests; those are filtered
    out via the paginator's ``keep`` predicate so every result is a true
    issue.
    """
    owner = validate_owner(owner)
    repo = validate_repo(repo)
    if state not in ISSUE_STATE_VALUES:
        raise ValidationError(f"state must be one of {sorted(ISSUE_STATE_VALUES)}.", field="state")
    if sort is not None and sort not in ISSUE_SORT_VALUES:
        raise ValidationError(
            f"sort must be one of {sorted(ISSUE_SORT_VALUES)} or omitted.", field="sort"
        )
    if direction not in DIRECTION_VALUES:
        raise ValidationError(
            f"direction must be one of {sorted(DIRECTION_VALUES)}.", field="direction"
        )
    if not 1 <= limit <= 100:
        raise ValidationError("limit must be between 1 and 100.", field="limit")
    clean_labels = _clean_labels(labels)

    params: dict[str, Any] = {"state": state, "direction": direction}
    if sort is not None:
        params["sort"] = sort
    if clean_labels:
        params["labels"] = ",".join(clean_labels)

    entries = await client.get_paginated(
        f"/repos/{owner}/{repo}/issues",
        params=params,
        max_items=limit,
        keep=_is_issue,
    )
    return [build_issue_response(entry) for entry in entries]


def build_issue_response(entry: Mapping[str, Any]) -> IssueResponse:
    return IssueResponse(
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
        labels=_label_names(entry.get("labels")),
        html_url=require_str(entry, "html_url"),
    )


def _is_issue(entry: Any) -> bool:
    """GitHub marks PRs inside issue payloads with a ``pull_request`` key."""
    return isinstance(entry, Mapping) and "pull_request" not in entry


def _clean_labels(labels: list[str] | None) -> list[str]:
    if labels is None:
        return []
    cleaned = [label.strip() for label in labels]
    unique = [label for label in cleaned if label]
    if len(unique) != len(cleaned):
        raise ValidationError("labels must be non-empty strings.", field="labels")
    if len(unique) > 20:
        raise ValidationError("labels accepts at most 20 names.", field="labels")
    return unique


def _label_names(labels_payload: Any) -> list[str]:
    if not isinstance(labels_payload, list):
        return []
    names: list[str] = []
    for label in labels_payload:
        if isinstance(label, Mapping) and isinstance(name := label.get("name"), str):
            names.append(name)
        elif isinstance(label, str):
            names.append(label)
    return names
