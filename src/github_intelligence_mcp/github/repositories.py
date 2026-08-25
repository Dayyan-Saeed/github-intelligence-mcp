"""Repository operations against the GitHub REST API.

Functions here fetch raw payloads and map them onto public response models.
They are MCP-agnostic and independently testable.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from github_intelligence_mcp.errors import GitHubAPIError
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.models.repository import RepositoryResponse
from github_intelligence_mcp.utils.validation import validate_owner, validate_repo


async def get_repository(client: GitHubClient, owner: str, repo: str) -> RepositoryResponse:
    """Fetch one repository and map it to :class:`RepositoryResponse`."""
    owner = validate_owner(owner)
    repo = validate_repo(repo)
    payload = await client.get_json(f"/repos/{owner}/{repo}")
    return build_repository_response(payload)


def build_repository_response(payload: Mapping[str, Any]) -> RepositoryResponse:
    """Map a raw ``GET /repos/{owner}/{repo}`` payload onto the public model.

    Mapping is explicit rather than alias-based so that tool output stays
    stable even if GitHub renames or adds API fields.
    """
    license_payload = payload.get("license")
    return RepositoryResponse(
        name=_require_str(payload, "name"),
        full_name=_require_str(payload, "full_name"),
        description=_optional_str(payload.get("description")),
        private=bool(payload.get("private", False)),
        fork=bool(payload.get("fork", False)),
        stars=_require_int(payload, "stargazers_count"),
        forks=_require_int(payload, "forks_count"),
        watchers=_require_int(payload, "watchers_count"),
        open_issues=_require_int(payload, "open_issues_count"),
        language=_optional_str(payload.get("language")),
        license=_license_label(license_payload),
        default_branch=_require_str(payload, "default_branch"),
        created_at=_require_str(payload, "created_at"),  # type: ignore[arg-type]
        updated_at=_require_str(payload, "updated_at"),  # type: ignore[arg-type]
        pushed_at=payload.get("pushed_at"),
        html_url=_require_str(payload, "html_url"),
    )


def _require(payload: Mapping[str, Any], key: str) -> Any:
    try:
        return payload[key]
    except KeyError as exc:
        raise GitHubAPIError(f"Unexpected GitHub API payload: missing '{key}'.") from exc


def _require_str(payload: Mapping[str, Any], key: str) -> str:
    value = _require(payload, key)
    if not isinstance(value, str):
        raise GitHubAPIError(f"Unexpected GitHub API payload: '{key}' is not a string.")
    return value


def _require_int(payload: Mapping[str, Any], key: str) -> int:
    value = _require(payload, key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise GitHubAPIError(f"Unexpected GitHub API payload: '{key}' is not an integer.")
    return value


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _license_label(license_payload: Any) -> str | None:
    if not isinstance(license_payload, dict):
        return None
    label = license_payload.get("spdx_id") or license_payload.get("name")
    if not isinstance(label, str) or label == "NOASSERTION":
        return None
    return label
