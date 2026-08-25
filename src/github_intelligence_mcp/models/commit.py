"""Commit response model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CommitResponse(BaseModel):
    """Structured commit information returned by ``get_recent_commits``.

    ``author``/``committer`` prefer the linked GitHub account login and fall
    back to the raw git name when no account is linked.
    """

    model_config = ConfigDict(frozen=True)

    sha: str
    message: str
    author: str | None
    author_date: datetime
    committer: str | None
    commit_date: datetime
    html_url: str
