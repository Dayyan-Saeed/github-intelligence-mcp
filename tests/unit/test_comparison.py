"""Tests for repository comparison."""

from conftest import issue_payload
from github_intelligence_mcp.analysis.comparison import compare_snapshots
from github_intelligence_mcp.analysis.health import build_health_response


def test_equal_repositories_yield_all_ties(snapshot_factory) -> None:  # type: ignore[no-untyped-def]
    snap = snapshot_factory()
    health = build_health_response(snap, stale_issue_days=90, stale_pr_days=30)
    comparison = compare_snapshots(snap, snap, health, health)

    assert comparison.repo_a.overall_score == comparison.repo_b.overall_score
    assert all(d.winner == "tie" for d in comparison.dimensions)


def test_better_repo_wins_dimensions(snapshot_factory) -> None:  # type: ignore[no-untyped-def]
    healthy = snapshot_factory()
    stale = snapshot_factory(
        open_issues=[issue_payload(i, created_days_ago=200) for i in range(15)],
        commits_last_30=[],
        contributors=[{"login": "solo", "contributions": 100, "avatar_url": "a", "html_url": "h"}],
    )

    h_healthy = build_health_response(healthy, stale_issue_days=90, stale_pr_days=30)
    h_stale = build_health_response(stale, stale_issue_days=90, stale_pr_days=30)
    comparison = compare_snapshots(healthy, stale, h_healthy, h_stale)

    overall = next(d for d in comparison.dimensions if d.dimension == "overall_health")
    assert overall.winner == "repo_a"
    assert float(overall.repo_a_value) > float(overall.repo_b_value)


def test_risk_report_independent_of_comparison(snapshot_factory) -> None:  # type: ignore[no-untyped-def]
    from github_intelligence_mcp.analysis.risks import aggregate_risk_level, detect_risks

    THRESHOLDS = {"stale_issue_days": 90, "stale_pr_days": 30}
    snap = snapshot_factory()
    risks = detect_risks(snap, **THRESHOLDS)
    assert aggregate_risk_level(risks) == "low"


def test_dimensions_include_all_health_components(snapshot_factory) -> None:  # type: ignore[no-untyped-def]
    snap_a = snapshot_factory()
    snap_b = snapshot_factory()
    h_a = build_health_response(snap_a, stale_issue_days=90, stale_pr_days=30)
    h_b = build_health_response(snap_b, stale_issue_days=90, stale_pr_days=30)
    comparison = compare_snapshots(snap_a, snap_b, h_a, h_b)

    expected = {
        "stars",
        "forks",
        "open_issues",
        "open_pulls",
        "commits_last_30",
        "releases_last_90",
        "activity",
        "issue_health",
        "pr_health",
        "contributor_health",
        "release_activity",
        "documentation",
        "overall_health",
    }
    actual = {d.dimension for d in comparison.dimensions}
    assert expected == actual
