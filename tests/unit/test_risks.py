"""Tests for maintenance risk detection."""

from datetime import UTC, datetime

from conftest import (
    AnalysisSnapshotFactory,
    contributor_payload,
    issue_payload,
    open_pr_payload,
    release_payload,
)
from github_intelligence_mcp.analysis.risks import (
    aggregate_risk_level,
    aggregate_risk_score,
    detect_risks,
)

THRESHOLDS = {"stale_issue_days": 90, "stale_pr_days": 30}


def test_healthy_repository_yields_no_risks(snapshot_factory: AnalysisSnapshotFactory) -> None:
    snapshot = snapshot_factory()
    risks = detect_risks(snapshot, **THRESHOLDS)
    assert risks == []
    assert aggregate_risk_level([]) == "low"
    assert aggregate_risk_score([]) == 0


def test_stale_issues_detected_with_severity_scaling(
    snapshot_factory: AnalysisSnapshotFactory,
) -> None:
    few = snapshot_factory(open_issues=[issue_payload(i, created_days_ago=200) for i in range(3)])
    many = snapshot_factory(open_issues=[issue_payload(i, created_days_ago=200) for i in range(12)])

    few_risks = detect_risks(few, **THRESHOLDS)
    many_risks = detect_risks(many, **THRESHOLDS)

    stale_few = next(r for r in few_risks if r.type == "stale_issues")
    stale_many = next(r for r in many_risks if r.type == "stale_issues")
    assert stale_few.severity == "low"
    assert stale_many.severity == "high"
    assert stale_many.evidence["stale_issue_count"] == 12


def test_inactive_repository_flagged_after_threshold(
    snapshot_factory: AnalysisSnapshotFactory,
) -> None:
    pushed_200d = snapshot_factory(pushed_days_ago=200)
    pushed_400d = snapshot_factory(pushed_days_ago=400)
    recent = snapshot_factory(pushed_days_ago=5)

    risk_200 = next(
        r for r in detect_risks(pushed_200d, **THRESHOLDS) if r.type == "inactive_repository"
    )
    risk_400 = next(
        r for r in detect_risks(pushed_400d, **THRESHOLDS) if r.type == "inactive_repository"
    )

    assert risk_200.severity == "medium"
    assert risk_400.severity == "high"
    assert not any(r.type == "inactive_repository" for r in detect_risks(recent, **THRESHOLDS))


def test_zero_commits_flags_low_activity(snapshot_factory: AnalysisSnapshotFactory) -> None:
    quiet = snapshot_factory(commits_last_30=[])
    risks = detect_risks(quiet, **THRESHOLDS)
    activity = [r for r in risks if r.type == "low_commit_activity"]
    assert len(activity) == 1
    assert activity[0].severity == "medium"


def test_single_active_contributor_is_high_bus_factor(
    snapshot_factory: AnalysisSnapshotFactory,
) -> None:
    solo = snapshot_factory(
        commits_authors=["alice"],
        contributors=[contributor_payload("alice", 500)],
    )
    risks = detect_risks(solo, **THRESHOLDS)
    bus = next(r for r in risks if r.type == "bus_factor")
    assert bus.severity == "high"


def test_concentration_reported_as_potential_not_verdict(
    snapshot_factory: AnalysisSnapshotFactory,
) -> None:
    concentrated = snapshot_factory(
        commits_authors=["alice", "bob"],
        contributors=[contributor_payload("alice", 950), contributor_payload("bob", 50)],
    )
    risks = detect_risks(concentrated, **THRESHOLDS)
    concentration = next(r for r in risks if r.type == "contributor_concentration")
    assert concentration.severity == "medium"
    assert "potential" in concentration.description.lower()


def test_long_release_gap_detected(snapshot_factory: AnalysisSnapshotFactory) -> None:
    stale_release = snapshot_factory(releases=[release_payload(days_ago=800, tag="v1.0")])
    fresh_release = snapshot_factory(releases=[release_payload(days_ago=30, tag="v2.0")])

    gap_risk = next(
        r for r in detect_risks(stale_release, **THRESHOLDS) if r.type == "long_release_gap"
    )
    assert gap_risk.severity == "high"
    assert not any(r.type == "long_release_gap" for r in detect_risks(fresh_release, **THRESHOLDS))


def test_drafts_and_prereleases_do_not_count_as_stable_releases(
    snapshot_factory: AnalysisSnapshotFactory,
) -> None:
    draft_only = {
        "releases": [
            {**release_payload(days_ago=1, tag="v2-rc"), "draft": False, "prerelease": True},
            {**release_payload(days_ago=900, tag="v1.0")},
        ]
    }
    snapshot = snapshot_factory(**draft_only, commits_last_30=None, commits_last_90=None)
    risks = detect_risks(snapshot, **THRESHOLDS)
    gap = next(r for r in risks if r.type == "long_release_gap")
    assert gap.evidence["last_published_at"].startswith("20")


def test_risk_score_is_bounded_and_additive(
    snapshot_factory: AnalysisSnapshotFactory,
) -> None:
    risky = snapshot_factory(
        open_issues=[issue_payload(i, created_days_ago=300) for i in range(15)],
        commits_last_30=[],
        pushed_days_ago=500,
    )
    risks = detect_risks(risky, **THRESHOLDS)
    score = aggregate_risk_score(risks)
    assert 0 < score <= 100
    assert aggregate_risk_level(risks) in {"medium", "high"}


def test_computed_at_uses_snapshot_clock(snapshot_factory: AnalysisSnapshotFactory) -> None:
    snapshot = snapshot_factory(now=datetime(2026, 1, 1, tzinfo=UTC))
    assert snapshot.now == datetime(2026, 1, 1, tzinfo=UTC)


def test_stale_prs_use_configured_threshold(
    snapshot_factory: AnalysisSnapshotFactory,
) -> None:
    prs = [
        open_pr_payload(1, created_days_ago=40),
        open_pr_payload(2, created_days_ago=40),
    ]
    strict = snapshot_factory(open_pulls=prs)
    relaxed = snapshot_factory(open_pulls=prs)

    strict_risks = detect_risks(strict, stale_issue_days=90, stale_pr_days=30)
    relaxed_risks = detect_risks(relaxed, stale_issue_days=90, stale_pr_days=60)

    assert any(r.type == "stale_pull_requests" for r in strict_risks)
    assert not any(r.type == "stale_pull_requests" for r in relaxed_risks)
