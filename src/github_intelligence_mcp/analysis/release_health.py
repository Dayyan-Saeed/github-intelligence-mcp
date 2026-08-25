"""Release activity score (weight: 10%).

Release cadence is one signal among many — frequent releases do not
automatically mean a healthier repository (spec §25), which is why this
component carries the smallest weight and uses gentle saturation targets.
"""

from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any

from github_intelligence_mcp.analysis.scoring import capped_ratio, days_between, mean, recency_score
from github_intelligence_mcp.models.release import ReleaseResponse

WEIGHT = 0.10
LABEL = "Release Activity"

_RELEASES_90_TARGET = 2
_RECENCY_FRESH_DAYS = 30.0
_RECENCY_STALE_DAYS = 365.0
_INTERVAL_HEALTHY_DAYS = 45.0
_NEUTRAL_CADENCE = 50


def compute_release_activity_score(
    *,
    releases_desc: list[ReleaseResponse],
    now: datetime,
) -> tuple[int, dict[str, Any]]:
    """Score release recency and cadence from newest-first release list."""
    published = [r for r in releases_desc if r.published_at is not None]
    published.sort(key=lambda r: r.published_at or r.created_at, reverse=True)

    releases_last_90 = sum(
        1 for r in published if days_between(r.published_at or r.created_at, now) <= 90
    )
    intervals: list[float] = []
    for older, newer in zip(published[1:], published):
        if older.published_at is not None and newer.published_at is not None:
            intervals.append(days_between(older.published_at, newer.published_at))
    median_interval = median(intervals) if intervals else None

    if published:
        days_since_last = days_between(published[0].published_at or published[0].created_at, now)
        recency = recency_score(
            days_since_last, fresh_days=_RECENCY_FRESH_DAYS, stale_days=_RECENCY_STALE_DAYS
        )
    else:
        days_since_last = None
        recency = 0

    cadence = (
        # Intervals of ~45 days or shorter earn full marks; twice as long
        # scores 50. Frequent-but-chaotic releases are not extra credit.
        capped_ratio(_INTERVAL_HEALTHY_DAYS / median_interval, target=1.0)
        if median_interval and median_interval > 0
        else (_NEUTRAL_CADENCE if len(published) == 1 else 0)
    )
    frequency = capped_ratio(releases_last_90, target=_RELEASES_90_TARGET)

    details: dict[str, Any] = {
        "release_count_total_sampled": len(releases_desc),
        "releases_last_90": releases_last_90,
        "days_since_last_release": round(days_since_last, 1)
        if days_since_last is not None
        else None,
        "median_release_interval_days": round(median_interval, 1) if median_interval else None,
        "cadence_score": cadence,
    }
    return mean([recency, frequency, cadence]), details
