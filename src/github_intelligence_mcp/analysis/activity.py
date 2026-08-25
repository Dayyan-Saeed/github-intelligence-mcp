"""Activity score (weight: 25%).

Measures how alive a repository currently is. All inputs are counts over
recent windows so the score reflects momentum rather than accumulated
historical size.
"""

from __future__ import annotations

from typing import Any

from github_intelligence_mcp.analysis.scoring import capped_ratio, mean

# Saturation targets: values at or above these earn full marks.
_COMMITS_30_TARGET = 30
_COMMITS_90_TARGET = 60
_CONTRIBUTORS_TARGET = 5
_PULL_REQUESTS_30_TARGET = 10
_RELEASES_90_TARGET = 2

WEIGHT = 0.25
LABEL = "Activity"


def compute_activity_score(
    *,
    commits_last_30: int,
    commits_last_90: int,
    active_contributors_last_30: int,
    pull_requests_last_30: int,
    releases_last_90: int,
) -> tuple[int, dict[str, Any]]:
    """Combine recent commit/PR/contributor/release signals into 0-100."""
    components = [
        capped_ratio(commits_last_30, target=_COMMITS_30_TARGET),
        capped_ratio(commits_last_90, target=_COMMITS_90_TARGET),
        capped_ratio(active_contributors_last_30, target=_CONTRIBUTORS_TARGET),
        capped_ratio(pull_requests_last_30, target=_PULL_REQUESTS_30_TARGET),
        capped_ratio(releases_last_90, target=_RELEASES_90_TARGET),
    ]
    details: dict[str, Any] = {
        "commits_last_30": commits_last_30,
        "commits_last_90": commits_last_90,
        "active_contributors_last_30": active_contributors_last_30,
        "pull_requests_last_30": pull_requests_last_30,
        "releases_last_90": releases_last_90,
    }
    return mean(components), details
