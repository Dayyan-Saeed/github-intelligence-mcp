"""Overall health aggregation.

Weights follow spec §20 exactly:

    overall = activity*0.25 + issue_health*0.20 + pr_health*0.20
            + contributor_health*0.15 + release_activity*0.10 + documentation*0.10

Every component must independently produce a 0-100 score; grades are a thin,
documented mapping over the weighted result.
"""

from __future__ import annotations

from typing import Any

from github_intelligence_mcp.analysis import activity as activity_module
from github_intelligence_mcp.analysis import contributor_health as contributor_module
from github_intelligence_mcp.analysis import documentation as documentation_module
from github_intelligence_mcp.analysis import issue_health as issue_module
from github_intelligence_mcp.analysis import pr_health as pr_module
from github_intelligence_mcp.analysis import release_health as release_module
from github_intelligence_mcp.analysis.activity import WEIGHT as ACTIVITY_WEIGHT
from github_intelligence_mcp.analysis.analyzer import AnalysisSnapshot
from github_intelligence_mcp.analysis.contributor_health import WEIGHT as CONTRIBUTOR_WEIGHT
from github_intelligence_mcp.analysis.documentation import WEIGHT as DOCUMENTATION_WEIGHT
from github_intelligence_mcp.analysis.issue_health import WEIGHT as ISSUE_WEIGHT
from github_intelligence_mcp.analysis.pr_health import WEIGHT as PR_WEIGHT
from github_intelligence_mcp.analysis.release_health import WEIGHT as RELEASE_WEIGHT
from github_intelligence_mcp.logging import get_logger
from github_intelligence_mcp.models.health import ComponentScore, RepositoryHealthResponse

_log = get_logger(__name__)

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


def build_health_response(
    snapshot: AnalysisSnapshot,
    *,
    stale_issue_days: int,
    stale_pr_days: int,
) -> RepositoryHealthResponse:
    """Score a pre-computed snapshot into a full health response.

    This is the shared engine used by both ``analyze_repository`` and
    ``compare_repositories`` — it takes a snapshot, scores it, and returns
    the complete response without touching the network.
    """
    now = snapshot.now

    activity_score, activity_details = activity_module.compute_activity_score(
        commits_last_30=len(snapshot.commits_30),
        commits_last_90=len(snapshot.commits_90),
        active_contributors_last_30=len(snapshot.active_authors_30),
        pull_requests_last_30=snapshot.opened_prs_30,
        releases_last_90=snapshot.releases_last_90,
    )
    issue_score, issue_details = issue_module.compute_issue_health_score(
        open_issues=snapshot.open_issues,
        created_last_90=snapshot.created_issues_90,
        closed_last_90=snapshot.closed_issues_90,
        now=now,
        stale_after_days=stale_issue_days,
    )
    pr_score, pr_details = pr_module.compute_pr_health_score(
        open_pull_requests=snapshot.open_pulls,
        merged_last_90=snapshot.merged_prs_90,
        opened_last_90=snapshot.opened_prs_90,
        now=now,
        stale_after_days=stale_pr_days,
    )
    contributor_score, contributor_details = contributor_module.compute_contributor_health_score(
        contributors=snapshot.contributors,
        active_contributors_last_30=len(
            snapshot.active_authors_30 & {c.username for c in snapshot.contributors}
        ),
    )
    release_score, release_details = release_module.compute_release_activity_score(
        releases_desc=snapshot.releases, now=now
    )
    documentation_score, documentation_details = documentation_module.compute_documentation_score(
        has_readme=snapshot.has_readme,
        has_license=snapshot.metadata.license is not None,
        has_description=bool(snapshot.metadata.description),
        has_homepage=bool(snapshot.metadata.homepage),
    )

    scored: dict[str, tuple[int, str, dict[str, Any]]] = {
        "activity": (activity_score, activity_module.LABEL, activity_details),
        "issue_health": (issue_score, issue_module.LABEL, issue_details),
        "pr_health": (pr_score, pr_module.LABEL, pr_details),
        "contributor_health": (
            contributor_score,
            contributor_module.LABEL,
            contributor_details,
        ),
        "release_activity": (release_score, release_module.LABEL, release_details),
        "documentation": (documentation_score, documentation_module.LABEL, documentation_details),
    }

    components = [
        ComponentScore(
            name=name, label=label, score=score, weight=COMPONENT_WEIGHTS[name], details=details
        )
        for name, (score, label, details) in scored.items()
    ]
    overall = compute_overall_score({name: values[0] for name, values in scored.items()})

    _log.info(
        "health scored owner=%s repo=%s overall=%d grade=%s",
        snapshot.owner,
        snapshot.repo,
        overall,
        score_to_grade(overall),
    )
    return RepositoryHealthResponse(
        owner=snapshot.owner,
        repo=snapshot.repo,
        overall_score=overall,
        grade=score_to_grade(overall),
        components=components,
        computed_at=now,
    )
