"""Maintenance risk detection (deterministic, evidence-backed).

Every detected risk carries machine-readable evidence so consumers can judge
the finding themselves. Severity thresholds are explicit and documented in
``docs/health-scoring.md``; concentration findings are phrased as *potential*
risks, never as verdicts.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from github_intelligence_mcp.analysis.analyzer import AnalysisSnapshot
from github_intelligence_mcp.analysis.scoring import days_between
from github_intelligence_mcp.models.health import RiskItem, Severity

_INACTIVE_AFTER_DAYS = 180.0
_DEAD_AFTER_DAYS = 365.0
_RELEASE_GAP_DAYS = 365.0
_RELEASE_GAP_CRITICAL_DAYS = 730.0
_ISSUE_AGE_DAYS = 365.0
_CONCENTRATION_THRESHOLD = 0.8

_SEVERITY_WEIGHTS: dict[str, int] = {"high": 25, "medium": 10, "low": 5}


def detect_risks(
    snapshot: AnalysisSnapshot,
    *,
    stale_issue_days: int,
    stale_pr_days: int,
) -> list[RiskItem]:
    """Run all risk rules against a repository snapshot."""
    risks: list[RiskItem] = []
    now = snapshot.now

    risks += _stale_issue_risks(snapshot, stale_issue_days)
    risks += _stale_pr_risks(snapshot, stale_pr_days)
    risks += _inactivity_risks(snapshot, now)
    risks += _contributor_risks(snapshot)
    risks += _release_gap_risks(snapshot, now)

    return risks


def aggregate_risk_level(risks: list[RiskItem]) -> Severity:
    """Highest severity present; ``low`` when nothing was detected."""
    if any(r.severity == "high" for r in risks):
        return "high"
    if any(r.severity == "medium" for r in risks):
        return "medium"
    return "low"


def aggregate_risk_score(risks: list[RiskItem]) -> int:
    """Bounded magnitude of detected risk (higher = more/riskier findings)."""
    total = sum(_SEVERITY_WEIGHTS.get(r.severity, 0) for r in risks)
    return min(100, total)


def _stale_issue_risks(snapshot: AnalysisSnapshot, stale_issue_days: int) -> list[RiskItem]:
    cutoff = snapshot.now - timedelta(days=stale_issue_days)
    stale = [i for i in snapshot.open_issues if i.updated_at < cutoff]
    if not stale:
        return []
    share = len(stale) / len(snapshot.open_issues) if snapshot.open_issues else 0.0
    # Noise floor: tiny backlogs with one-or-two stale entries stay "low".
    severity: Severity
    if len(stale) >= 10 and share >= 0.5:
        severity = "high"
    elif len(stale) >= 5:
        severity = "medium"
    else:
        severity = "low"
    return [
        RiskItem(
            type="stale_issues",
            severity=severity,
            description=(
                f"{len(stale)} open issue(s) have not been updated in over {stale_issue_days} days."
            ),
            evidence={
                "stale_issue_count": len(stale),
                "open_issue_count": len(snapshot.open_issues),
                "stale_after_days": stale_issue_days,
            },
        )
    ]


def _stale_pr_risks(snapshot: AnalysisSnapshot, stale_pr_days: int) -> list[RiskItem]:
    cutoff = snapshot.now - timedelta(days=stale_pr_days)
    stale = [pr for pr in snapshot.open_pulls if pr.created_at < cutoff and pr.merged_at is None]
    if not stale:
        return []
    severity: Severity = "medium" if len(stale) >= 5 else "low"
    if len(stale) >= 15:
        severity = "high"
    return [
        RiskItem(
            type="stale_pull_requests",
            severity=severity,
            description=(
                f"{len(stale)} open pull request(s) have been waiting longer than "
                f"{stale_pr_days} days."
            ),
            evidence={
                "stale_pull_request_count": len(stale),
                "open_pull_request_count": len(snapshot.open_pulls),
                "stale_after_days": stale_pr_days,
                "oldest_open_pull_request_days": round(
                    max(days_between(pr.created_at, snapshot.now) for pr in snapshot.open_pulls), 1
                )
                if snapshot.open_pulls
                else None,
            },
        )
    ]


def _inactivity_risks(snapshot: AnalysisSnapshot, now: datetime) -> list[RiskItem]:
    risks: list[RiskItem] = []

    pushed_at = snapshot.metadata.pushed_at
    if pushed_at is not None:
        days_since_push = days_between(pushed_at, now)
        if days_since_push >= _DEAD_AFTER_DAYS:
            severity: Severity = "high"
        elif days_since_push >= _INACTIVE_AFTER_DAYS:
            severity = "medium"
        else:
            severity = "low"
        if days_since_push >= _INACTIVE_AFTER_DAYS:
            risks.append(
                RiskItem(
                    type="inactive_repository",
                    severity=severity,
                    description=(
                        f"No pushes for {round(days_since_push)} days; the repository "
                        "appears inactive."
                    ),
                    evidence={
                        "days_since_last_push": round(days_since_push, 1),
                        "pushed_at": pushed_at.isoformat(),
                    },
                )
            )

    commit_count_30 = len(snapshot.commits_30)
    if commit_count_30 == 0:
        risks.append(
            RiskItem(
                type="low_commit_activity",
                severity="medium",
                description="No commits found in the last 30 days.",
                evidence={"commits_last_30": 0},
            )
        )
    elif commit_count_30 <= 2:
        risks.append(
            RiskItem(
                type="low_commit_activity",
                severity="low",
                description=f"Only {commit_count_30} commit(s) in the last 30 days.",
                evidence={"commits_last_30": commit_count_30},
            )
        )

    if snapshot.open_issues:
        average_age = sum(days_between(i.created_at, now) for i in snapshot.open_issues) / len(
            snapshot.open_issues
        )
        if average_age >= _ISSUE_AGE_DAYS:
            risks.append(
                RiskItem(
                    type="aging_open_issues",
                    severity="medium",
                    description=(
                        f"Average open-issue age is {round(average_age)} days, "
                        "suggesting backlog neglect."
                    ),
                    evidence={
                        "average_open_issue_age_days": round(average_age, 1),
                        "threshold_days": _ISSUE_AGE_DAYS,
                    },
                )
            )

    return risks


def _contributor_risks(snapshot: AnalysisSnapshot) -> list[RiskItem]:
    risks: list[RiskItem] = []
    contributors = sorted(snapshot.contributors, key=lambda c: c.contributions, reverse=True)
    total = sum(c.contributions for c in contributors)

    if contributors and total > 0:
        top1_share = contributors[0].contributions / total
        if top1_share >= _CONCENTRATION_THRESHOLD:
            risks.append(
                RiskItem(
                    type="contributor_concentration",
                    severity="medium",
                    description=(
                        "Potential contributor concentration risk: the most active "
                        f"contributor accounts for {round(top1_share * 100)}% of "
                        "recently sampled contributions."
                    ),
                    evidence={
                        "top1_share": round(top1_share, 3),
                        "threshold": _CONCENTRATION_THRESHOLD,
                        "note": (
                            "A signal only; concentration does not by itself prove "
                            "the project is unhealthy."
                        ),
                    },
                )
            )

    active = len(snapshot.active_authors_30)
    if active == 0:
        pass  # already covered by low_commit_activity
    elif active == 1:
        risks.append(
            RiskItem(
                type="bus_factor",
                severity="high",
                description="Only one contributor authored commits in the last 30 days.",
                evidence={"active_contributors_last_30": 1},
            )
        )
    elif active <= 2:
        risks.append(
            RiskItem(
                type="bus_factor",
                severity="medium",
                description=f"Only {active} contributors authored commits in the last 30 days.",
                evidence={"active_contributors_last_30": active},
            )
        )

    return risks


def _release_gap_risks(snapshot: AnalysisSnapshot, now: datetime) -> list[RiskItem]:
    published = [
        r
        for r in snapshot.releases
        if r.published_at is not None and not r.draft and not r.prerelease
    ]
    if not published:
        return [
            RiskItem(
                type="no_releases",
                severity="low",
                description="No published releases found in the sampled history.",
                evidence={"published_release_count_sampled": len(published)},
            )
        ]

    latest = max(r.published_at for r in published if r.published_at is not None)
    gap = days_between(latest, now)
    if gap >= _RELEASE_GAP_CRITICAL_DAYS:
        severity: Severity = "high"
    elif gap >= _RELEASE_GAP_DAYS:
        severity = "medium"
    else:
        return []

    return [
        RiskItem(
            type="long_release_gap",
            severity=severity,
            description=(
                f"Latest stable release was {round(gap)} days ago, which may indicate "
                "a stalled release cadence."
            ),
            evidence={
                "days_since_last_stable_release": round(gap, 1),
                "last_published_at": latest.isoformat(),
            },
        )
    ]
