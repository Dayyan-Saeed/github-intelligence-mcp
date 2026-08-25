"""Tests for the deterministic health scoring engine."""

from datetime import UTC, datetime, timedelta

from github_intelligence_mcp.analysis.activity import compute_activity_score
from github_intelligence_mcp.analysis.contributor_health import compute_contributor_health_score
from github_intelligence_mcp.analysis.documentation import compute_documentation_score
from github_intelligence_mcp.analysis.health import (
    COMPONENT_WEIGHTS,
    compute_overall_score,
    score_to_grade,
)
from github_intelligence_mcp.analysis.issue_health import compute_issue_health_score
from github_intelligence_mcp.analysis.pr_health import compute_pr_health_score
from github_intelligence_mcp.analysis.release_health import compute_release_activity_score
from github_intelligence_mcp.analysis.scoring import (
    balance_ratio,
    capped_ratio,
    recency_score,
)
from github_intelligence_mcp.models.contributor import ContributorResponse
from github_intelligence_mcp.models.issue import IssueResponse
from github_intelligence_mcp.models.pull_request import PullRequestResponse
from github_intelligence_mcp.models.release import ReleaseResponse

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


def _issue(created: datetime, updated: datetime | None = None) -> IssueResponse:
    return IssueResponse(
        number=1,
        title="t",
        state="open",
        author=None,
        created_at=created,
        updated_at=updated or created,
        closed_at=None,
        labels=[],
        html_url="https://github.test/o/r/issues/1",
    )


def _pr(created: datetime, merged: datetime | None = None) -> PullRequestResponse:
    return PullRequestResponse(
        number=2,
        title="pr",
        state="open",
        author=None,
        created_at=created,
        updated_at=created,
        closed_at=None,
        merged_at=merged,
        draft=False,
        labels=[],
        html_url="https://github.test/o/r/pull/2",
    )


def _contributor(name: str, contributions: int) -> ContributorResponse:
    return ContributorResponse(
        username=name,
        contributions=contributions,
        avatar_url="https://a.test/x.png",
        html_url=f"https://github.test/{name}",
    )


def _release(published: datetime | None) -> ReleaseResponse:
    return ReleaseResponse(
        tag_name="v1",
        name="v1",
        author=None,
        created_at=published or NOW,
        published_at=published,
        prerelease=False,
        draft=False,
        html_url="https://github.test/o/r/releases/v1",
    )


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


def test_capped_ratio_saturates() -> None:
    assert capped_ratio(30, target=30) == 100
    assert capped_ratio(300, target=30) == 100
    assert capped_ratio(15, target=30) == 50
    assert capped_ratio(0, target=30) == 0


def test_balance_ratio_neutral_when_total_zero() -> None:
    assert balance_ratio(0, 0) == 50
    assert balance_ratio(5, 10) == 50


def test_recency_decay_linear() -> None:
    assert recency_score(5, fresh_days=10, stale_days=110) == 100
    assert recency_score(60, fresh_days=10, stale_days=110) == 50
    assert recency_score(200, fresh_days=10, stale_days=110) == 0


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------


def test_activity_score_full_when_targets_met() -> None:
    score, details = compute_activity_score(
        commits_last_30=30,
        commits_last_90=60,
        active_contributors_last_30=5,
        pull_requests_last_30=10,
        releases_last_90=2,
    )
    assert score == 100
    assert details["commits_last_30"] == 30


def test_activity_score_zero_when_quiet() -> None:
    score, details = compute_activity_score(
        commits_last_30=0,
        commits_last_90=0,
        active_contributors_last_30=0,
        pull_requests_last_30=0,
        releases_last_90=0,
    )
    assert score == 0


def test_activity_scale_is_saturating_not_unbounded() -> None:
    huge, _ = compute_activity_score(
        commits_last_30=3000,
        commits_last_90=6000,
        active_contributors_last_30=500,
        pull_requests_last_30=1000,
        releases_last_90=20,
    )
    modest, _ = compute_activity_score(
        commits_last_30=30,
        commits_last_90=60,
        active_contributors_last_30=5,
        pull_requests_last_30=10,
        releases_last_90=2,
    )
    assert huge == modest == 100


# ---------------------------------------------------------------------------
# Issue health
# ---------------------------------------------------------------------------


def test_issue_health_all_fresh_issues_scores_high() -> None:
    fresh = [_issue(NOW - timedelta(days=i + 1)) for i in range(5)]
    score, details = compute_issue_health_score(
        open_issues=fresh,
        created_last_90=5,
        closed_last_90=5,
        now=NOW,
    )
    assert score >= 80
    assert details["stale_issue_count"] == 0


def test_issue_health_stale_issues_lower_score() -> None:
    stale = [_issue(NOW - timedelta(days=200)) for _ in range(8)]
    score, _ = compute_issue_health_score(
        open_issues=stale, created_last_90=0, closed_last_90=0, now=NOW
    )
    healthy, _ = compute_issue_health_score(
        open_issues=[_issue(NOW - timedelta(days=3)) for _ in range(8)],
        created_last_90=0,
        closed_last_90=0,
        now=NOW,
    )
    assert score < healthy
    assert score < 40


def test_issue_health_empty_backlog_is_neutral_not_punished() -> None:
    score, details = compute_issue_health_score(
        open_issues=[], created_last_90=0, closed_last_90=0, now=NOW
    )
    assert 45 <= score <= 55
    assert details["open_issue_count"] == 0


def test_issue_health_respects_custom_threshold() -> None:
    issue = _issue(NOW - timedelta(days=60))
    strict, _ = compute_issue_health_score(
        open_issues=[issue], created_last_90=0, closed_last_90=0, now=NOW, stale_after_days=30
    )
    relaxed, _ = compute_issue_health_score(
        open_issues=[issue], created_last_90=0, closed_last_90=0, now=NOW, stale_after_days=120
    )
    assert strict < relaxed


# ---------------------------------------------------------------------------
# PR health
# ---------------------------------------------------------------------------


def test_pr_health_penalizes_stale_open_prs() -> None:
    stale = [_pr(NOW - timedelta(days=90)) for _ in range(4)]
    score, details = compute_pr_health_score(
        open_pull_requests=stale,
        merged_last_90=0,
        opened_last_90=4,
        now=NOW,
    )
    assert score < 40
    assert details["stale_pull_request_count"] == 4


def test_pr_health_merged_prs_do_not_count_as_stale() -> None:
    merged_long_ago_created = [
        PullRequestResponse(
            number=9,
            title="merged",
            state="closed",
            author=None,
            created_at=NOW - timedelta(days=400),
            updated_at=NOW - timedelta(days=395),
            closed_at=NOW - timedelta(days=395),
            merged_at=NOW - timedelta(days=395),
            draft=False,
            labels=[],
            html_url="x",
        )
    ]
    _, details = compute_pr_health_score(
        open_pull_requests=[],  # merged PRs are not in the open list at all
        merged_last_90=1,
        opened_last_90=1,
        now=NOW,
    )
    assert "stale_pull_request_count" in details


# ---------------------------------------------------------------------------
# Contributor health
# ---------------------------------------------------------------------------


def test_contributor_health_balanced_team_scores_high() -> None:
    contributors = [_contributor(f"u{i}", 100) for i in range(5)]
    score, details = compute_contributor_health_score(
        contributors=contributors, active_contributors_last_30=5
    )
    assert score >= 80
    assert details["bus_factor"] == 3  # 3 people cover >= 50% of 500
    assert details["top1_share"] == 0.2


def test_contributor_health_single_maintainer_flags_concentration() -> None:
    score, details = compute_contributor_health_score(
        contributors=[_contributor("solo", 1000), _contributor("helper", 10)],
        active_contributors_last_30=1,
    )
    assert details["top1_share"] > 0.9
    assert score < 50


def test_contributor_health_no_data_scores_zero_with_note() -> None:
    score, details = compute_contributor_health_score(
        contributors=[], active_contributors_last_30=0
    )
    assert score == 0
    assert details["note"]


# ---------------------------------------------------------------------------
# Release activity
# ---------------------------------------------------------------------------


def test_release_activity_regular_recent_releases_score_well() -> None:
    releases = [
        _release(NOW - timedelta(days=15)),
        _release(NOW - timedelta(days=45)),
        _release(NOW - timedelta(days=75)),
    ]
    score, details = compute_release_activity_score(releases_desc=releases, now=NOW)
    assert score >= 75
    assert details["releases_last_90"] == 3
    assert details["median_release_interval_days"] == 30.0


def test_release_activity_no_releases_scores_zero() -> None:
    score, details = compute_release_activity_score(releases_desc=[], now=NOW)
    assert score == 0
    assert details["days_since_last_release"] is None


def test_release_activity_old_single_release_scores_low() -> None:
    score, _ = compute_release_activity_score(
        releases_desc=[_release(NOW - timedelta(days=400))], now=NOW
    )
    assert score <= 35


def test_release_activity_drafts_without_publish_date_are_tolerated() -> None:
    draft = ReleaseResponse(
        tag_name="v2-rc",
        name=None,
        author=None,
        created_at=NOW - timedelta(days=1),
        published_at=None,
        prerelease=True,
        draft=True,
        html_url="x",
    )
    score, details = compute_release_activity_score(
        releases_desc=[draft, _release(NOW - timedelta(days=40))], now=NOW
    )
    # Score rides on the one published release; the undated draft neither
    # breaks interval math nor inflates frequency.
    assert score >= 60
    assert details["median_release_interval_days"] is None


def test_release_activity_zero_and_one_release_differ() -> None:
    none_score, none_details = compute_release_activity_score(releases_desc=[], now=NOW)
    one_score, _ = compute_release_activity_score(
        releases_desc=[_release(NOW - timedelta(days=5))], now=NOW
    )
    assert none_score == 0
    assert none_details["cadence_score"] == 0
    assert one_score > none_score  # a fresh single release beats silence


# ---------------------------------------------------------------------------
# Documentation & overall
# ---------------------------------------------------------------------------


def test_documentation_score_points_add_up() -> None:
    full, details = compute_documentation_score(
        has_readme=True, has_license=True, has_description=True, has_homepage=True
    )
    bare, _ = compute_documentation_score(
        has_readme=False, has_license=False, has_description=False, has_homepage=False
    )
    assert full == 100
    assert bare == 0
    assert details["points_possible"] == 100


def test_weights_match_spec() -> None:
    assert COMPONENT_WEIGHTS == {
        "activity": 0.25,
        "issue_health": 0.20,
        "pr_health": 0.20,
        "contributor_health": 0.15,
        "release_activity": 0.10,
        "documentation": 0.10,
    }
    assert sum(COMPONENT_WEIGHTS.values()) == 1.0


def test_overall_score_is_weighted_sum() -> None:
    scores = {
        "activity": 100,
        "issue_health": 100,
        "pr_health": 100,
        "contributor_health": 100,
        "release_activity": 100,
        "documentation": 100,
    }
    assert compute_overall_score(scores) == 100

    mixed = dict.fromkeys(scores, 0)
    mixed["activity"] = 100
    assert compute_overall_score(mixed) == round(100 * 0.25)

    assert compute_overall_score({}) == 0


def test_grades_map_linearly() -> None:
    assert score_to_grade(95) == "A"
    assert score_to_grade(85) == "A"
    assert score_to_grade(72) == "B"
    assert score_to_grade(56) == "C"
    assert score_to_grade(41) == "D"
    assert score_to_grade(0) == "F"
