"""Repository analysis orchestrator.

Fetches a bounded sample of repository data through the ``github`` service
layer and computes the deterministic health assessment defined in
``docs/health-scoring.md``. Pure scorers do the math; this module only
gathers inputs and assembles evidence.

Sampling honesty: each endpoint contributes at most ~100 items (Phase 1
limits), so very high-volume repositories may undercount raw totals. Sample
sizes are included in component details.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from github_intelligence_mcp.analysis import (
    activity as activity_module,
)
from github_intelligence_mcp.analysis import (
    contributor_health as contributor_module,
)
from github_intelligence_mcp.analysis import (
    documentation as documentation_module,
)
from github_intelligence_mcp.analysis import (
    issue_health as issue_module,
)
from github_intelligence_mcp.analysis import (
    pr_health as pr_module,
)
from github_intelligence_mcp.analysis import (
    release_health as release_module,
)
from github_intelligence_mcp.analysis.health import (
    COMPONENT_WEIGHTS,
    compute_overall_score,
    score_to_grade,
)
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.commits import get_recent_commits
from github_intelligence_mcp.github.contributors import get_contributors
from github_intelligence_mcp.github.issues import get_issues
from github_intelligence_mcp.github.pull_requests import get_pull_requests
from github_intelligence_mcp.github.releases import get_releases
from github_intelligence_mcp.github.repositories import get_repository, readme_exists
from github_intelligence_mcp.logging import get_logger
from github_intelligence_mcp.models.commit import CommitResponse
from github_intelligence_mcp.models.contributor import ContributorResponse
from github_intelligence_mcp.models.health import ComponentScore, RepositoryHealthResponse
from github_intelligence_mcp.models.issue import IssueResponse
from github_intelligence_mcp.models.pull_request import PullRequestResponse
from github_intelligence_mcp.models.release import ReleaseResponse
from github_intelligence_mcp.models.repository import RepositoryResponse
from github_intelligence_mcp.utils.validation import validate_owner, validate_repo

_SAMPLE_LIMIT = 100

_log = get_logger("analysis.analyzer")


@dataclass(frozen=True)
class AnalysisSnapshot:
    """Bounded sample of repository data used by all analysis tools."""

    owner: str
    repo: str
    now: datetime
    metadata: RepositoryResponse
    has_readme: bool
    open_issues: list[IssueResponse]
    closed_issues: list[IssueResponse]
    open_pulls: list[PullRequestResponse]
    closed_pulls: list[PullRequestResponse]
    commits_30: list[CommitResponse]
    commits_90: list[CommitResponse]
    contributors: list[ContributorResponse]
    releases: list[ReleaseResponse]

    @property
    def created_issues_90(self) -> int:
        cutoff = self.now - timedelta(days=90)
        return sum(1 for i in self.open_issues if i.created_at >= cutoff)

    @property
    def closed_issues_90(self) -> int:
        cutoff = self.now - timedelta(days=90)
        return sum(
            1 for i in self.closed_issues if i.closed_at is not None and i.closed_at >= cutoff
        )

    @property
    def opened_prs_30(self) -> int:
        cutoff = self.now - timedelta(days=30)
        return sum(1 for pr in self.open_pulls if pr.created_at >= cutoff)

    @property
    def opened_prs_90(self) -> int:
        cutoff = self.now - timedelta(days=90)
        return sum(1 for pr in self.open_pulls if pr.created_at >= cutoff)

    @property
    def merged_prs_90(self) -> int:
        cutoff = self.now - timedelta(days=90)
        return sum(
            1 for pr in self.closed_pulls if pr.merged_at is not None and pr.merged_at >= cutoff
        )

    @property
    def releases_last_90(self) -> int:
        cutoff = self.now - timedelta(days=90)
        return sum(
            1 for r in self.releases if r.published_at is not None and r.published_at >= cutoff
        )

    @property
    def active_authors_30(self) -> set[str]:
        return {c.author for c in self.commits_30 if c.author}


async def gather_snapshot(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    now: datetime | None = None,
) -> AnalysisSnapshot:
    """Fetch the bounded data sample shared by analysis and risk tools."""
    owner = validate_owner(owner)
    repo = validate_repo(repo)
    now = now or datetime.now(UTC)

    metadata = await get_repository(client, owner, repo)
    has_readme = await readme_exists(client, owner, repo)
    open_issues = await get_issues(client, owner, repo, state="open", limit=_SAMPLE_LIMIT)
    closed_issues = await get_issues(
        client, owner, repo, state="closed", sort="updated", limit=_SAMPLE_LIMIT
    )
    open_pulls = await get_pull_requests(client, owner, repo, state="open", limit=_SAMPLE_LIMIT)
    closed_pulls = await get_pull_requests(
        client, owner, repo, state="closed", sort="updated", limit=_SAMPLE_LIMIT
    )
    commits_30 = await get_recent_commits(client, owner, repo, days=30, limit=_SAMPLE_LIMIT)
    commits_90 = await get_recent_commits(client, owner, repo, days=90, limit=_SAMPLE_LIMIT)
    contributors = await get_contributors(client, owner, repo, limit=_SAMPLE_LIMIT)
    releases = await get_releases(client, owner, repo, limit=_SAMPLE_LIMIT)

    return AnalysisSnapshot(
        owner=owner,
        repo=repo,
        now=now,
        metadata=metadata,
        has_readme=has_readme,
        open_issues=open_issues,
        closed_issues=closed_issues,
        open_pulls=open_pulls,
        closed_pulls=closed_pulls,
        commits_30=commits_30,
        commits_90=commits_90,
        contributors=contributors,
        releases=releases,
    )


async def analyze_repository(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    stale_issue_days: int = 90,
    stale_pr_days: int = 30,
    now: datetime | None = None,
) -> RepositoryHealthResponse:
    """Compute the full deterministic health assessment for one repository."""
    snapshot = await gather_snapshot(client, owner, repo, now=now)
    now = snapshot.now

    _log.info("analyze start owner=%s repo=%s", snapshot.owner, snapshot.repo)

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
        "analyze done owner=%s repo=%s overall=%d grade=%s",
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
