"""Contributor operations against the GitHub REST API."""

from __future__ import annotations

from typing import Any

from github_intelligence_mcp.errors import ValidationError
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.payloads import require_int, require_str
from github_intelligence_mcp.models.contributor import ContributorResponse
from github_intelligence_mcp.utils.validation import validate_owner, validate_repo


async def get_contributors(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    limit: int = 30,
) -> list[ContributorResponse]:
    """Fetch up to ``limit`` contributors for a repository.

    Anonymous contributor entries (which carry no ``login``) are skipped by
    design: the public model requires a stable username.
    """
    owner = validate_owner(owner)
    repo = validate_repo(repo)
    if not 1 <= limit <= 100:
        raise ValidationError("limit must be between 1 and 100.", field="limit")
    # A single page suffices because limit is capped at 100 (GitHub's maximum
    # page size); this keeps contributor fetches to one HTTP round trip.
    entries = await client.get_paginated(
        f"/repos/{owner}/{repo}/contributors", max_items=limit, per_page=limit
    )
    return [build_contributor_response(entry) for entry in entries if _has_login(entry)]


def build_contributor_response(entry: Any) -> ContributorResponse:
    if not isinstance(entry, dict):
        raise ValueError(
            "contributor entry must be a mapping"
        )  # pragma: no cover - guarded upstream
    return ContributorResponse(
        username=require_str(entry, "login"),
        contributions=require_int(entry, "contributions"),
        avatar_url=require_str(entry, "avatar_url"),
        html_url=require_str(entry, "html_url"),
    )


def _has_login(entry: Any) -> bool:
    return isinstance(entry, dict) and isinstance(entry.get("login"), str)
