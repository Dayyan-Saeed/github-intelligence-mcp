"""Side-by-side repository comparison (deterministic, no LLM).

Runs two independent health analyses and contrasts them across explicit
dimensions. Each dimension names a winner when the values are numeric and
unequal; ``tie`` when equal; ``None`` for non-numeric fields.
"""

from __future__ import annotations

from typing import Literal

from github_intelligence_mcp.analysis.analyzer import AnalysisSnapshot
from github_intelligence_mcp.models.health import (
    ComparisonDimension,
    RepositoryComparisonResponse,
    RepositoryHealthResponse,
)

_Winner = Literal["repo_a", "repo_b", "tie"]


def _pick_winner(a: int, b: int) -> _Winner:
    if a > b:
        return "repo_a"
    if b > a:
        return "repo_b"
    return "tie"


def compare_snapshots(
    snapshot_a: AnalysisSnapshot,
    snapshot_b: AnalysisSnapshot,
    health_a: RepositoryHealthResponse,
    health_b: RepositoryHealthResponse,
) -> RepositoryComparisonResponse:
    """Build a comparison report from two pre-computed snapshots and health results."""
    now = max(snapshot_a.now, snapshot_b.now)
    components_a = {c.name: c for c in health_a.components}
    components_b = {c.name: c for c in health_b.components}

    dimensions: list[ComparisonDimension] = []

    # Repo-level stats
    repo_stats: list[tuple[str, int, int]] = [
        ("stars", snapshot_a.metadata.stars, snapshot_b.metadata.stars),
        ("forks", snapshot_a.metadata.forks, snapshot_b.metadata.forks),
        ("open_issues", len(snapshot_a.open_issues), len(snapshot_b.open_issues)),
        ("open_pulls", len(snapshot_a.open_pulls), len(snapshot_b.open_pulls)),
        ("commits_last_30", len(snapshot_a.commits_30), len(snapshot_b.commits_30)),
        ("releases_last_90", snapshot_a.releases_last_90, snapshot_b.releases_last_90),
    ]
    for dim_name, val_a, val_b in repo_stats:
        winner: _Winner = _pick_winner(val_a, val_b)
        dimensions.append(
            ComparisonDimension(
                dimension=dim_name, repo_a_value=val_a, repo_b_value=val_b, winner=winner
            )
        )

    # Health score dimensions
    for name in [
        "activity",
        "issue_health",
        "pr_health",
        "contributor_health",
        "release_activity",
        "documentation",
    ]:
        ca = components_a.get(name)
        cb = components_b.get(name)
        if ca is None or cb is None:
            continue
        sa, sb = ca.score, cb.score
        w: _Winner = _pick_winner(sa, sb)
        dimensions.append(
            ComparisonDimension(dimension=name, repo_a_value=sa, repo_b_value=sb, winner=w)
        )

    # Overall
    ow: _Winner = _pick_winner(health_a.overall_score, health_b.overall_score)
    dimensions.append(
        ComparisonDimension(
            dimension="overall_health",
            repo_a_value=health_a.overall_score,
            repo_b_value=health_b.overall_score,
            winner=ow,
        )
    )

    return RepositoryComparisonResponse(
        repo_a=health_a,
        repo_b=health_b,
        dimensions=dimensions,
        computed_at=now,
    )
