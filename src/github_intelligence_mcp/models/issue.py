"""Issue response model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IssueResponse(BaseModel):
    """Structured issue information returned by ``get_issues``.

    Pull requests returned by GitHub's issues endpoint are filtered out
    before mapping; every instance represents a true issue.
    """

    model_config = ConfigDict(frozen=True)

    number: int
    title: str
    state: str
    author: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    labels: list[str]
    html_url: str
