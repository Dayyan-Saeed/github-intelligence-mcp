"""Contributor response model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ContributorResponse(BaseModel):
    """Structured contributor information returned by ``get_contributors``."""

    model_config = ConfigDict(frozen=True)

    username: str
    contributions: int
    avatar_url: str
    html_url: str
