"""Tests for the FastAPI API wrapper."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import github_intelligence_mcp.api as api_module
from github_intelligence_mcp.models.commit import CommitResponse
from github_intelligence_mcp.models.health import (
    ComponentScore,
    RepositoryHealthResponse,
)
from github_intelligence_mcp.models.issue import IssueResponse
from github_intelligence_mcp.models.pull_request import PullRequestResponse
from github_intelligence_mcp.models.repository import RepositoryResponse


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:

    from fastapi import APIRouter
    from fastapi.routing import APIRoute

    mock_client = MagicMock()
    mock_client.stale_issue_days = 90
    mock_client.stale_pr_days = 30
    api_module._client = mock_client

    test_app = FastAPI()
    router = APIRouter()
    for route in api_module.app.routes:
        if isinstance(route, APIRoute):
            router.add_api_route(route.path, route.endpoint, methods=route.methods)
    test_app.include_router(router)
    with TestClient(test_app) as c:
        yield c
    api_module._client = None


def _commit() -> CommitResponse:
    return CommitResponse(
        sha="abc1234567890",
        message="feat: add feature",
        author="octocat",
        author_date=datetime(2026, 1, 1, tzinfo=UTC),
        committer="octocat",
        commit_date=datetime(2026, 1, 1, tzinfo=UTC),
        html_url="https://github.com/octocat/Hello-World/commit/abc123",
    )


def _issue() -> IssueResponse:
    return IssueResponse(
        number=1,
        title="Bug report",
        state="open",
        author="user1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        closed_at=None,
        labels=[],
        html_url="https://github.com/octocat/Hello-World/issues/1",
    )


def _pull_request() -> PullRequestResponse:
    return PullRequestResponse(
        number=10,
        title="Add feature",
        state="open",
        author="user2",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        closed_at=None,
        merged_at=None,
        draft=False,
        labels=[],
        html_url="https://github.com/octocat/Hello-World/pull/10",
    )


class TestAPIEndpoints:
    @patch("github_intelligence_mcp.api.get_repository", new_callable=AsyncMock)
    def test_get_repository(self, mock_get_repo: AsyncMock, client: TestClient) -> None:
        mock_get_repo.return_value = RepositoryResponse(
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
            default_branch="main",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
            pushed_at=datetime(2026, 1, 1, tzinfo=UTC),
            html_url="https://github.com/octocat/Hello-World",
        )
        response = client.get("/api/repository/octocat/Hello-World")
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "octocat/Hello-World"
        assert data["stars"] == 100

    @patch("github_intelligence_mcp.api.build_health_response")
    @patch("github_intelligence_mcp.api.gather_snapshot", new_callable=AsyncMock)
    def test_analyze_repository(
        self,
        mock_snapshot: AsyncMock,
        mock_health: MagicMock,
        client: TestClient,
    ) -> None:
        @dataclass
        class FakeSnapshot:
            metadata: object = None
            issues_open: list[object] | None = None
            issues_closed_recently: list[object] | None = None
            prs_open: list[object] | None = None
            prs_merged_recently: list[object] | None = None
            commits: list[object] | None = None
            contributors: list[object] | None = None
            releases: list[object] | None = None
            now: datetime | None = None

            def __post_init__(self) -> None:
                if self.issues_open is None:
                    self.issues_open = []
                if self.issues_closed_recently is None:
                    self.issues_closed_recently = []
                if self.prs_open is None:
                    self.prs_open = []
                if self.prs_merged_recently is None:
                    self.prs_merged_recently = []
                if self.commits is None:
                    self.commits = []
                if self.contributors is None:
                    self.contributors = []
                if self.releases is None:
                    self.releases = []
                if self.now is None:
                    self.now = datetime(2026, 1, 1, tzinfo=UTC)

        mock_snapshot.return_value = FakeSnapshot()
        mock_health.return_value = RepositoryHealthResponse(
            owner="octocat",
            repo="Hello-World",
            overall_score=75,
            grade="B",
            components=[
                ComponentScore(name="activity", label="Activity", score=80, weight=0.25, details={})
            ],
            computed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

        response = client.get("/api/repository/octocat/Hello-World/health")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 75
        assert data["grade"] == "B"

    @patch("github_intelligence_mcp.api.get_recent_commits", new_callable=AsyncMock)
    def test_get_commits(self, mock_commits: AsyncMock, client: TestClient) -> None:
        mock_commits.return_value = [_commit()]
        response = client.get("/api/repository/octocat/Hello-World/commits")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["sha"] == "abc1234567890"

    @patch("github_intelligence_mcp.api.get_issues", new_callable=AsyncMock)
    def test_get_issues(self, mock_issues: AsyncMock, client: TestClient) -> None:
        mock_issues.return_value = [_issue()]
        response = client.get("/api/repository/octocat/Hello-World/issues")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["number"] == 1

    @patch("github_intelligence_mcp.api.get_pull_requests", new_callable=AsyncMock)
    def test_get_pulls(self, mock_pulls: AsyncMock, client: TestClient) -> None:
        mock_pulls.return_value = [_pull_request()]
        response = client.get("/api/repository/octocat/Hello-World/pulls")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["number"] == 10
