"""Repository health analysis models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ComponentScore(BaseModel):
    """One scored component of the overall health algorithm.

    ``score`` is an integer in 0-100; ``weight`` is that component's share of
    the overall score (all weights sum to 1.0); ``details`` carries the raw
    evidence so every score is explainable.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    label: str
    score: int = Field(ge=0, le=100)
    weight: float
    details: dict[str, Any]


class RepositoryHealthResponse(BaseModel):
    """Overall deterministic health assessment of one repository.

    Computed entirely in code — no LLM involvement — using the documented
    formulas in ``docs/health-scoring.md``.
    """

    model_config = ConfigDict(frozen=True)

    owner: str
    repo: str
    overall_score: int = Field(ge=0, le=100)
    grade: str
    components: list[ComponentScore]
    computed_at: datetime
