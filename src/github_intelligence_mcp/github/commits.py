"""Commit operations against the GitHub REST API."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from github_intelligence_mcp.errors import GitHubAPIError, ValidationError
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.payloads import (
    optional_login,
    optional_str,
    parse_datetime,
    require,
    require_str,
)
from github_intelligence_mcp.models.commit import CommitResponse
from github_intelligence_mcp.utils.validation import validate_owner, validate_repo


async def get_recent_commits(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    days: int = 30,
    limit: int = 30,
) -> list[CommitResponse]:
    """Fetch up to ``limit`` commits pushed within the last ``days`` days."""
    owner = validate_owner(owner)
    repo = validate_repo(repo)
    if not 1 <= days <= 365:
        raise ValidationError("days must be between 1 and 365.", field="days")
    if not 1 <= limit <= 100:
        raise ValidationError("limit must be between 1 and 100.", field="limit")

    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    entries = await client.get_paginated(
        f"/repos/{owner}/{repo}/commits",
        params={"since": since},
        max_items=limit,
    )
    return [build_commit_response(entry) for entry in entries]


def build_commit_response(entry: Mapping[str, Any]) -> CommitResponse:
    commit_obj = _require_mapping(require(entry, "commit"), "commit")
    git_author = _require_mapping(commit_obj.get("author"), "commit.author")
    git_committer = _require_mapping(commit_obj.get("committer"), "commit.committer")

    return CommitResponse(
        sha=require_str(entry, "sha"),
        message=require_str(commit_obj, "message"),
        author=_person_name(git_author, entry.get("author")),
        author_date=parse_datetime(require_str(git_author, "date"), field="commit.author.date"),
        committer=_person_name(git_committer, entry.get("committer")),
        commit_date=parse_datetime(
            require_str(git_committer, "date"), field="commit.committer.date"
        ),
        html_url=require_str(entry, "html_url"),
    )


def _person_name(git_person: Mapping[str, Any], github_user: Any) -> str | None:
    """Prefer the linked GitHub account login; fall back to the git name."""
    login = optional_login(github_user)
    if login is not None:
        return login
    return optional_str(git_person.get("name"))


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GitHubAPIError(f"Unexpected GitHub API payload: '{field}' is not an object.")
    return value
