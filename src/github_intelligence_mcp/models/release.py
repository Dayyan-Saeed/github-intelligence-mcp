"""Release response model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReleaseResponse(BaseModel):
    """Structured release information returned by ``get_releases``.

    ``published_at`` is ``None`` for draft releases.
    """

    model_config = ConfigDict(frozen=True)

    tag_name: str
    name: str | None
    author: str | None
    created_at: datetime
    published_at: datetime | None
    prerelease: bool
    draft: bool
    html_url: str
