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
from github_intelligence_mcp.models.health import ComponentScore, RepositoryHealthResponse
from github_intelligence_mcp.utils.validation import validate_owner, validate_repo

_SAMPLE_LIMIT = 100

_log = get_logger("analysis.analyzer")


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
    owner = validate_owner(owner)
    repo = validate_repo(repo)
    now = now or datetime.now(UTC)

    _log.info("analyze start owner=%s repo=%s", owner, repo)
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

    cutoff_90 = now - timedelta(days=90)
    cutoff_30 = now - timedelta(days=30)

    created_issues_90 = sum(1 for i in open_issues if i.created_at >= cutoff_90)
    closed_issues_90 = sum(
        1 for i in closed_issues if i.closed_at is not None and i.closed_at >= cutoff_90
    )
    opened_prs_90 = sum(1 for pr in open_pulls if pr.created_at >= cutoff_90)
    merged_prs_90 = sum(
        1 for pr in closed_pulls if pr.merged_at is not None and pr.merged_at >= cutoff_90
    )
    opened_prs_30 = sum(1 for pr in open_pulls if pr.created_at >= cutoff_30)
    active_authors_30 = {c.author for c in commits_30 if c.author}

    activity_score, activity_details = activity_module.compute_activity_score(
        commits_last_30=len(commits_30),
        commits_last_90=len(commits_90),
        active_contributors_last_30=len(active_authors_30),
        pull_requests_last_30=opened_prs_30,
        releases_last_90=sum(
            1 for r in releases if r.published_at is not None and r.published_at >= cutoff_90
        ),
    )
    issue_score, issue_details = issue_module.compute_issue_health_score(
        open_issues=open_issues,
        created_last_90=created_issues_90,
        closed_last_90=closed_issues_90,
        now=now,
        stale_after_days=stale_issue_days,
    )
    pr_score, pr_details = pr_module.compute_pr_health_score(
        open_pull_requests=open_pulls,
        merged_last_90=merged_prs_90,
        opened_last_90=opened_prs_90,
        now=now,
        stale_after_days=stale_pr_days,
    )
    contributor_score, contributor_details = contributor_module.compute_contributor_health_score(
        contributors=contributors,
        active_contributors_last_30=len(active_authors_30 & {c.username for c in contributors}),
    )
    release_score, release_details = release_module.compute_release_activity_score(
        releases_desc=releases, now=now
    )
    documentation_score, documentation_details = documentation_module.compute_documentation_score(
        has_readme=has_readme,
        has_license=metadata.license is not None,
        has_description=bool(metadata.description),
        has_homepage=bool(metadata.homepage),
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
        owner,
        repo,
        overall,
        score_to_grade(overall),
    )
    return RepositoryHealthResponse(
        owner=owner,
        repo=repo,
        overall_score=overall,
        grade=score_to_grade(overall),
        components=components,
        computed_at=now,
    )
