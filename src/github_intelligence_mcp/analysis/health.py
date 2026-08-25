"""Overall health aggregation.

Weights follow spec §20 exactly:

    overall = activity*0.25 + issue_health*0.20 + pr_health*0.20
            + contributor_health*0.15 + release_activity*0.10 + documentation*0.10

Every component must independently produce a 0-100 score; grades are a thin,
documented mapping over the weighted result.
"""

from __future__ import annotations

from github_intelligence_mcp.analysis.activity import WEIGHT as ACTIVITY_WEIGHT
from github_intelligence_mcp.analysis.contributor_health import WEIGHT as CONTRIBUTOR_WEIGHT
from github_intelligence_mcp.analysis.documentation import WEIGHT as DOCUMENTATION_WEIGHT
from github_intelligence_mcp.analysis.issue_health import WEIGHT as ISSUE_WEIGHT
from github_intelligence_mcp.analysis.pr_health import WEIGHT as PR_WEIGHT
from github_intelligence_mcp.analysis.release_health import WEIGHT as RELEASE_WEIGHT

COMPONENT_WEIGHTS: dict[str, float] = {
    "activity": ACTIVITY_WEIGHT,
    "issue_health": ISSUE_WEIGHT,
    "pr_health": PR_WEIGHT,
    "contributor_health": CONTRIBUTOR_WEIGHT,
    "release_activity": RELEASE_WEIGHT,
    "documentation": DOCUMENTATION_WEIGHT,
}

GRADE_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (85, "A"),
    (70, "B"),
    (55, "C"),
    (40, "D"),
    (0, "F"),
)


def compute_overall_score(scores_by_name: dict[str, int]) -> int:
    """Weighted overall score from component scores; missing components count as 0."""
    total = sum(scores_by_name.get(name, 0) * weight for name, weight in COMPONENT_WEIGHTS.items())
    return round(total)


def score_to_grade(score: int) -> str:
    """Map an overall score onto its letter grade."""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"  # pragma: no cover - threshold 0 makes this unreachable
