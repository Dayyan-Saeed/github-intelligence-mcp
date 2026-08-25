"""Shared deterministic math for health scoring.

Every scorer maps raw signals onto a 0-100 score using saturating ratios:
``value`` earns ``score_target`` points per unit until the cap. This keeps
extremely large repositories from being unfairly favored (a repo with 500
commits/month scores no better than one with 30) while staying fully
explainable.
"""

from __future__ import annotations

from datetime import datetime


def capped_ratio(value: float, *, target: float) -> int:
    """Score ``value`` against a saturation target; both must be >= 0."""
    if target <= 0 or value <= 0:
        return 0
    return min(100, round(value / target * 100))


def balance_ratio(part: float, total: float, *, neutral: int = 50) -> int:
    """Percentage score for ``part`` of ``total``, or ``neutral`` when undefined.

    Used where zero data is genuinely uninformative (e.g. no issues ever
    closed *and* none opened): guessing 0 would punish quiet repositories
    unfairly and 100 would reward them without evidence.
    """
    if total <= 0:
        return neutral
    return capped_ratio(part, target=total)


def days_between(earlier: datetime, later: datetime) -> float:
    """Whole-day distance between two datetimes (negative-safe)."""
    delta = later - earlier
    return max(0.0, delta.total_seconds() / 86400)


def recency_score(days: float, *, fresh_days: float, stale_days: float) -> int:
    """Linear decay from 100 at ``fresh_days`` to 0 at ``stale_days``."""
    if days <= fresh_days:
        return 100
    if days >= stale_days:
        return 0
    span = stale_days - fresh_days
    remaining = (stale_days - days) / span
    return round(remaining * 100)


def mean(values: list[int]) -> int:
    """Arithmetic mean rounded to nearest int; 0 for an empty set."""
    if not values:
        return 0
    return round(sum(values) / len(values))
