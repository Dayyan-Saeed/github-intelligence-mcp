"""Issue health score (weight: 20%).

Signals: share of open issues gone stale, closure throughput versus inflow,
and the average age of still-open issues.

Stale definition (documented, configurable via ``stale_issue_days``): an
open issue whose last update is older than the threshold.
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
from github_intelligence_mcp.models.issue import IssueResponse

WEIGHT = 0.20
LABEL = "Issue Health"

_AGE_FRESH_DAYS = 30.0
_AGE_DEAD_DAYS = 365.0
_NEUTRAL_BALANCE = 50


def compute_issue_health_score(
    *,
    open_issues: list[IssueResponse],
    created_last_90: int,
    closed_last_90: int,
    now: datetime,
    stale_after_days: int = 90,
) -> tuple[int, dict[str, Any]]:
    """Score issue backlog health from open issues plus 90-day flow counts."""
    stale_cutoff = now - timedelta(days=stale_after_days)

    # No backlog and no recent flow means we know nothing about issue
    # handling — report a neutral score rather than a lucky 100.
    if not open_issues and created_last_90 == 0 and closed_last_90 == 0:
        return 50, {
            "open_issue_count": 0,
            "note": "No open issues and no recent issue flow; insufficient signal.",
        }

    stale_count = sum(1 for issue in open_issues if issue.updated_at < stale_cutoff)
    stale_share = stale_count / len(open_issues) if open_issues else 0.0

    ages = [days_between(issue.created_at, now) for issue in open_issues]
    average_age = sum(ages) / len(ages) if ages else 0.0

    freshness = round((1 - stale_share) * 100)
    flow_balance = balance_ratio(
        closed_last_90, closed_last_90 + created_last_90, neutral=_NEUTRAL_BALANCE
    )
    age_score = recency_score(average_age, fresh_days=_AGE_FRESH_DAYS, stale_days=_AGE_DEAD_DAYS)

    details: dict[str, Any] = {
        "open_issue_count": len(open_issues),
        "stale_issue_count": stale_count,
        "stale_after_days": stale_after_days,
        "created_last_90": created_last_90,
        "closed_last_90": closed_last_90,
        "average_open_age_days": round(average_age, 1),
    }
    return mean([freshness, flow_balance, age_score]), details
