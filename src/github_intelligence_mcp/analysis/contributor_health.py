"""Contributor health score (weight: 15%).

Signals: how many contributors are active recently, and how concentrated
contributions are. High concentration is reported as a *potential* risk
factor — it is a signal, not proof of unhealthiness.
"""

from __future__ import annotations

from typing import Any

from github_intelligence_mcp.analysis.scoring import capped_ratio, mean
from github_intelligence_mcp.models.contributor import ContributorResponse

WEIGHT = 0.15
LABEL = "Contributor Health"

_ACTIVE_CONTRIBUTOR_TARGET = 5


def compute_contributor_health_score(
    *,
    contributors: list[ContributorResponse],
    active_contributors_last_30: int,
) -> tuple[int, dict[str, Any]]:
    """Score contributor base breadth and balance.

    ``contributors`` is the ranked contribution list; concentration is derived
    from the top-1 share and the bus-factor proxy (fewest people covering 50%
    of all contributions).
    """
    total_contributions = sum(c.contributions for c in contributors)
    if total_contributions <= 0 or not contributors:
        return 0, {
            "contributor_count": len(contributors),
            "active_contributors_last_30": active_contributors_last_30,
            "top1_share": None,
            "bus_factor": None,
            "note": "No contribution data available.",
        }

    ranked = sorted(contributors, key=lambda c: c.contributions, reverse=True)
    top1_share = ranked[0].contributions / total_contributions

    covered = 0
    bus_factor = 0
    for person in ranked:
        covered += person.contributions
        bus_factor += 1
        if covered >= total_contributions / 2:
            break

    diversity = round((1 - top1_share) * 100)
    breadth = capped_ratio(active_contributors_last_30, target=_ACTIVE_CONTRIBUTOR_TARGET)

    details: dict[str, Any] = {
        "contributor_count": len(ranked),
        "active_contributors_last_30": active_contributors_last_30,
        "top1_share": round(top1_share, 3),
        "bus_factor": bus_factor,
        "total_contributions": total_contributions,
    }
    return mean([diversity, breadth]), details
