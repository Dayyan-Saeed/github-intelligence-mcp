"""Repository response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RepositorySummary(BaseModel):
    """Compact repository representation used inside search results."""

    model_config = ConfigDict(frozen=True)

    name: str
    full_name: str
    description: str | None
    stars: int
    forks: int
    language: str | None
    html_url: str


class RepositoryResponse(BaseModel):
    """Structured repository information returned by the ``get_repository`` tool.

    Note: ``open_issues`` mirrors GitHub's ``open_issues_count``, which counts
    both issues and pull requests — this is a documented GitHub quirk.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    full_name: str
    description: str | None
    private: bool
    fork: bool
    stars: int
    forks: int
    watchers: int
    open_issues: int
    language: str | None
    license: str | None
    default_branch: str
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime | None
    html_url: str
