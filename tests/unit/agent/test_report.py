"""Tests for the investigation agent report generator."""

from datetime import UTC, datetime

from github_intelligence_mcp.agent import InvestigationState
from github_intelligence_mcp.agent.report import generate_report
from github_intelligence_mcp.models.commit import CommitResponse
from github_intelligence_mcp.models.health import (
    ComponentScore,
    MaintenanceRiskResponse,
    RepositoryHealthResponse,
    RiskItem,
)
from github_intelligence_mcp.models.issue import IssueResponse
from github_intelligence_mcp.models.pull_request import PullRequestResponse
from github_intelligence_mcp.models.repository import RepositoryResponse

NOW = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)


def _repo_metadata() -> RepositoryResponse:
    return RepositoryResponse(
        name="Hello-World",
        full_name="octocat/Hello-World",
        description="Test repo",
        private=False,
        fork=False,
        stars=100,
        forks=25,
        watchers=10,
        open_issues=5,
        language="Python",
        license="MIT",
        homepage="https://example.com",
        created_at=NOW,
        updated_at=NOW,
        pushed_at=NOW,
        default_branch="main",
        html_url="https://github.com/octocat/Hello-World",
    )


def _health() -> RepositoryHealthResponse:
    return RepositoryHealthResponse(
        owner="octocat",
        repo="Hello-World",
        overall_score=75,
        grade="B",
        components=[
            ComponentScore(name="activity", label="Activity", score=80, weight=0.25, details={}),
            ComponentScore(
                name="issue_health", label="Issue Health", score=70, weight=0.20, details={}
            ),
        ],
        computed_at=NOW,
    )


def _risks() -> MaintenanceRiskResponse:
    return MaintenanceRiskResponse(
        owner="octocat",
        repo="Hello-World",
        risk_level="medium",
        risk_score=15,
        risks=[
            RiskItem(
                type="stale_issues",
                severity="medium",
                description="3 open issues stale.",
                evidence={"stale_issue_count": 3},
            )
        ],
        computed_at=NOW,
    )


def test_report_includes_all_sections() -> None:
    state = InvestigationState(
        owner="octocat",
        repo="Hello-World",
        metadata=_repo_metadata(),
        health=_health(),
        risks=_risks(),
        recent_commits=[
            CommitResponse(
                sha="abc1234567",
                message="fix: resolve bug",
                author="alice",
                author_date=NOW,
                committer="alice",
                commit_date=NOW,
                html_url="https://github.com/octocat/Hello-World/commit/abc1234567",
            )
        ],
        open_issues=[
            IssueResponse(
                number=1,
                title="Bug report",
                state="open",
                author="bob",
                created_at=NOW,
                updated_at=NOW,
                closed_at=None,
                labels=[],
                html_url="https://github.com/octocat/Hello-World/issues/1",
            )
        ],
        open_pulls=[
            PullRequestResponse(
                number=10,
                title="Add feature",
                state="open",
                author="carol",
                created_at=NOW,
                updated_at=NOW,
                closed_at=None,
                merged_at=None,
                draft=False,
                labels=[],
                html_url="https://github.com/octocat/Hello-World/pull/10",
            )
        ],
    )

    report = generate_report(state)

    assert "# Investigation: octocat/Hello-World" in report
    assert "## Repository Overview" in report
    assert "## Health Assessment" in report
    assert "75/100" in report
    assert "grade B" in report
    assert "## Maintenance Risks" in report
    assert "medium" in report
    assert "## Recent Commits" in report
    assert "abc1234" in report
    assert "## Open Issues" in report
    assert "#1: Bug report" in report
    assert "## Open Pull Requests" in report
    assert "#10: Add feature" in report


def test_report_with_errors() -> None:
    state = InvestigationState(
        owner="o",
        repo="r",
        errors=["fetch_metadata: 404 Not Found"],
    )
    report = generate_report(state)
    assert "## Errors" in report
    assert "fetch_metadata: 404 Not Found" in report


def test_report_with_empty_state() -> None:
    state = InvestigationState(owner="o", repo="r")
    report = generate_report(state)
    assert "# Investigation: o/r" in report
