"""Shared input validation helpers.

These validators are a security boundary: they guarantee that owner/repo
values can never alter the URL path structure (no slashes, ``..``, or
encoded traversal), because they only allow a strict allow-list charset.
"""

from __future__ import annotations

import re

from github_intelligence_mcp.errors import ValidationError

# GitHub usernames: alphanumeric plus single interior hyphens, max 39 chars.
_OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")

# Repository names: letters, digits, '.', '_', '-' (GitHub also allows these),
# capped at 100 characters. The first character must be alphanumeric so that
# values like "." or ".." can never alter URL path structure.
_REPO_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def validate_owner(value: str, *, field: str = "owner") -> str:
    """Validate a repository owner (user or organization) login."""
    candidate = value.strip()
    if not _OWNER_PATTERN.fullmatch(candidate):
        raise ValidationError(
            f"'{field}' must be a valid GitHub username: letters and digits with "
            "single interior hyphens, up to 39 characters.",
            field=field,
        )
    return candidate


def validate_repo(value: str, *, field: str = "repo") -> str:
    """Validate a repository name."""
    candidate = value.strip()
    if not _REPO_PATTERN.fullmatch(candidate):
        raise ValidationError(
            f"'{field}' must be a valid repository name: letters, digits, "
            "'.', '_', or '-', up to 100 characters.",
            field=field,
        )
    return candidate
