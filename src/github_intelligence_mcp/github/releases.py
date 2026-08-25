"""Release operations against the GitHub REST API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from github_intelligence_mcp.errors import ValidationError
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.payloads import (
    optional_login,
    optional_str,
    parse_datetime,
    require_str,
)
from github_intelligence_mcp.models.release import ReleaseResponse
from github_intelligence_mcp.utils.validation import validate_owner, validate_repo


async def get_releases(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    limit: int = 30,
) -> list[ReleaseResponse]:
    """Fetch up to ``limit`` most recent releases for a repository."""
    owner = validate_owner(owner)
    repo = validate_repo(repo)
    if not 1 <= limit <= 100:
        raise ValidationError("limit must be between 1 and 100.", field="limit")
    # A single page suffices because limit is capped at 100 (GitHub's maximum
    # page size); this keeps release fetches to one HTTP round trip.
    entries = await client.get_paginated(
        f"/repos/{owner}/{repo}/releases", max_items=limit, per_page=limit
    )
    return [build_release_response(entry) for entry in entries]


def build_release_response(entry: Mapping[str, Any]) -> ReleaseResponse:
    """Map a raw release payload onto :class:`ReleaseResponse`.

    ``published_at`` is null for drafts; ``created_at`` is always present and
    used as the guaranteed timestamp.
    """
    return ReleaseResponse(
        tag_name=require_str(entry, "tag_name"),
        name=optional_str(entry.get("name")),
        author=optional_login(entry.get("author")),
        created_at=parse_datetime(require_str(entry, "created_at"), field="created_at"),
        published_at=(
            parse_datetime(published, field="published_at")
            if (published := entry.get("published_at"))
            else None
        ),
        prerelease=bool(entry.get("prerelease", False)),
        draft=bool(entry.get("draft", False)),
        html_url=require_str(entry, "html_url"),
    )
