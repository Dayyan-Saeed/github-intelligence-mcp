"""Pull request health score (weight: 20%).

Signals: share of open PRs gone stale, merge throughput versus inflow over
90 days, and average age of open PRs.

Stale definition (documented, configurable via ``stale_pr_days``): an open
PR untouched for longer than the threshold.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from github_intelligence_mcp.analysis.scoring import (
    balance_ratio,
    days_between,
    mean,
    recency_score,
)
from github_intelligence_mcp.models.pull_request import PullRequestResponse

WEIGHT = 0.20
LABEL = "Pull Request Health"

_AGE_FRESH_DAYS = 14.0
_AGE_DEAD_DAYS = 180.0
_NEUTRAL_BALANCE = 50


def compute_pr_health_score(
    *,
    open_pull_requests: list[PullRequestResponse],
    merged_last_90: int,
    opened_last_90: int,
    now: datetime,
    stale_after_days: int = 30,
) -> tuple[int, dict[str, Any]]:
    """Score PR pipeline health from open PRs plus 90-day merge/open flow."""
    stale_cutoff = now - timedelta(days=stale_after_days)
    stale_count = sum(
        1 for pr in open_pull_requests if pr.created_at < stale_cutoff and pr.merged_at is None
    )
    stale_share = stale_count / len(open_pull_requests) if open_pull_requests else 0.0

    ages = [days_between(pr.created_at, now) for pr in open_pull_requests]
    average_age = sum(ages) / len(ages) if ages else 0.0

    freshness = round((1 - stale_share) * 100)
    throughput = balance_ratio(
        merged_last_90, merged_last_90 + opened_last_90, neutral=_NEUTRAL_BALANCE
    )
    age_score = recency_score(average_age, fresh_days=_AGE_FRESH_DAYS, stale_days=_AGE_DEAD_DAYS)

    details: dict[str, Any] = {
        "open_pull_request_count": len(open_pull_requests),
        "stale_pull_request_count": stale_count,
        "stale_after_days": stale_after_days,
        "opened_last_90": opened_last_90,
        "merged_last_90": merged_last_90,
        "average_open_age_days": round(average_age, 1),
    }
    return mean([freshness, throughput, age_score]), details
