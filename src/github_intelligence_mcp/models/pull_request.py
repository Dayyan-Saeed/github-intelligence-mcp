"""Pull request response model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PullRequestResponse(BaseModel):
    """Structured pull request information returned by ``get_pull_requests``."""

    model_config = ConfigDict(frozen=True)

    number: int
    title: str
    state: str
    author: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    merged_at: datetime | None
    draft: bool
    labels: list[str]
    html_url: str
