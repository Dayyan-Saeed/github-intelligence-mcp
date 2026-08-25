"""Repository and repository-search operations against the GitHub REST API.

Functions here fetch raw payloads and map them onto public response models.
They are MCP-agnostic and independently testable.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from github_intelligence_mcp.errors import GitHubAPIError, GitHubNotFoundError, ValidationError
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.payloads import (
    optional_str,
    parse_datetime,
    require,
    require_int,
    require_str,
)
from github_intelligence_mcp.models.repository import (
    RepositoryResponse,
    RepositorySummary,
    SearchRepositoriesResponse,
)
from github_intelligence_mcp.utils.validation import validate_owner, validate_query, validate_repo

SEARCH_SORT_VALUES = frozenset({"stars", "forks", "help-wanted-issues", "updated"})
SEARCH_ORDER_VALUES = frozenset({"asc", "desc"})


async def get_repository(client: GitHubClient, owner: str, repo: str) -> RepositoryResponse:
    """Fetch one repository and map it to :class:`RepositoryResponse`."""
    owner = validate_owner(owner)
    repo = validate_repo(repo)
    payload = await client.get_json(f"/repos/{owner}/{repo}")
    return build_repository_response(payload)


async def search_repositories(
    client: GitHubClient,
    query: str,
    *,
    sort: str | None = None,
    order: str = "desc",
    limit: int = 30,
) -> SearchRepositoriesResponse:
    """Search repositories and return structured summaries.

    ``sort`` accepts stars/forks/help-wanted-issues/updated; ``None`` uses
    GitHub's best-match ordering. A single page of at most ``limit`` results
    is requested — search pagination is deliberately not followed.
    """
    query = validate_query(query)
    if sort is not None and sort not in SEARCH_SORT_VALUES:
        raise ValidationError(
            f"sort must be one of {sorted(SEARCH_SORT_VALUES)} or omitted.", field="sort"
        )
    if order not in SEARCH_ORDER_VALUES:
        raise ValidationError(f"order must be one of {sorted(SEARCH_ORDER_VALUES)}.", field="order")
    if not 1 <= limit <= 100:
        raise ValidationError("limit must be between 1 and 100.", field="limit")

    params: dict[str, Any] = {"q": query, "per_page": limit, "order": order}
    if sort is not None:
        params["sort"] = sort
    payload = await client.get_json("/search/repositories", params=params)
    return build_search_response(payload)


async def readme_exists(client: GitHubClient, owner: str, repo: str) -> bool:
    """Return whether the repository has a README (404-safe probe)."""
    owner = validate_owner(owner)
    repo = validate_repo(repo)
    try:
        await client.get_json(f"/repos/{owner}/{repo}/readme")
    except GitHubNotFoundError:
        return False
    return True


def build_repository_response(payload: Mapping[str, Any]) -> RepositoryResponse:
    """Map a raw ``GET /repos/{owner}/{repo}`` payload onto the public model.

    Mapping is explicit rather than alias-based so that tool output stays
    stable even if GitHub renames or adds API fields.
    """
    license_payload = payload.get("license")
    return RepositoryResponse(
        name=require_str(payload, "name"),
        full_name=require_str(payload, "full_name"),
        description=optional_str(payload.get("description")),
        private=bool(payload.get("private", False)),
        fork=bool(payload.get("fork", False)),
        stars=require_int(payload, "stargazers_count"),
        forks=require_int(payload, "forks_count"),
        watchers=require_int(payload, "watchers_count"),
        open_issues=require_int(payload, "open_issues_count"),
        language=optional_str(payload.get("language")),
        license=_license_label(license_payload),
        default_branch=require_str(payload, "default_branch"),
        created_at=parse_datetime(require_str(payload, "created_at"), field="created_at"),
        updated_at=parse_datetime(require_str(payload, "updated_at"), field="updated_at"),
        pushed_at=(
            parse_datetime(pushed, field="pushed_at")
            if (pushed := payload.get("pushed_at"))
            else None
        ),
        html_url=require_str(payload, "html_url"),
        homepage=optional_str(payload.get("homepage")),
    )


def build_search_response(payload: Mapping[str, Any]) -> SearchRepositoriesResponse:
    items_payload = require(payload, "items")
    if not isinstance(items_payload, list):
        raise GitHubAPIError("Unexpected GitHub API payload: 'items' is not a list.")
    return SearchRepositoriesResponse(
        total_count=require_int(payload, "total_count"),
        incomplete_results=bool(payload.get("incomplete_results", False)),
        items=[build_repository_summary(item) for item in items_payload],
    )


def build_repository_summary(item: Mapping[str, Any]) -> RepositorySummary:
    return RepositorySummary(
        name=require_str(item, "name"),
        full_name=require_str(item, "full_name"),
        description=optional_str(item.get("description")),
        stars=require_int(item, "stargazers_count"),
        forks=require_int(item, "forks_count"),
        language=optional_str(item.get("language")),
        html_url=require_str(item, "html_url"),
    )


def _license_label(license_payload: Any) -> str | None:
    if not isinstance(license_payload, dict):
        return None
    label = license_payload.get("spdx_id") or license_payload.get("name")
    if not isinstance(label, str) or label == "NOASSERTION":
        return None
    return label
