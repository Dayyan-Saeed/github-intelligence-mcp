"""Investigation report generator.

Produces a structured Markdown report from the completed investigation state.
The report is deterministic — no LLM involved — and summarizes all findings
in a format suitable for human review or LLM consumption.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from github_intelligence_mcp.agent import InvestigationState


def generate_report(state: InvestigationState) -> str:
    """Build a Markdown report from the investigation state."""
    lines: list[str] = []

    lines.append(f"# Investigation: {state.owner}/{state.repo}")
    lines.append("")

    # Metadata
    if state.metadata:
        m = state.metadata
        lines.append("## Repository Overview")
        lines.append("")
        lines.append(f"- **Description**: {m.description or 'N/A'}")
        lines.append(f"- **Language**: {m.language or 'N/A'}")
        lines.append(f"- **Stars**: {m.stars}")
        lines.append(f"- **Forks**: {m.forks}")
        lines.append(f"- **License**: {m.license or 'N/A'}")
        lines.append(f"- **Default branch**: {m.default_branch}")
        lines.append("")

    # Health
    if state.health:
        h = state.health
        lines.append("## Health Assessment")
        lines.append("")
        lines.append(f"- **Overall score**: {h.overall_score}/100 (grade {h.grade})")
        lines.append("")
        lines.append("| Component | Score | Weight |")
        lines.append("|-----------|-------|--------|")
        for c in h.components:
            lines.append(f"| {c.label} | {c.score} | {int(c.weight * 100)}% |")
        lines.append("")

    # Risks
    if state.risks:
        r = state.risks
        lines.append("## Maintenance Risks")
        lines.append("")
        lines.append(f"- **Risk level**: {r.risk_level}")
        lines.append(f"- **Risk score**: {r.risk_score}/100")
        lines.append("")
        if r.risks:
            for risk in r.risks:
                lines.append(f"### [{risk.severity.upper()}] {risk.type}")
                lines.append("")
                lines.append(risk.description)
                lines.append("")
                if risk.evidence:
                    lines.append("**Evidence:**")
                    for k, v in risk.evidence.items():
                        lines.append(f"- `{k}`: {v}")
                    lines.append("")
        else:
            lines.append("No maintenance risks detected.")
            lines.append("")

    # Recent activity
    if state.recent_commits:
        lines.append("## Recent Commits")
        lines.append("")
        for commit in state.recent_commits[:10]:
            author = commit.author or "unknown"
            date = commit.commit_date.strftime("%Y-%m-%d") if commit.commit_date else "unknown"
            lines.append(
                f"- `{commit.sha[:7]}` {commit.message.splitlines()[0]} ({author}, {date})"
            )
        lines.append("")

    # Open issues
    if state.open_issues:
        lines.append(f"## Open Issues ({len(state.open_issues)} shown)")
        lines.append("")
        for issue in state.open_issues[:10]:
            lines.append(f"- #{issue.number}: {issue.title}")
        lines.append("")

    # Open PRs
    if state.open_pulls:
        lines.append(f"## Open Pull Requests ({len(state.open_pulls)} shown)")
        lines.append("")
        for pr in state.open_pulls:
            lines.append(f"- #{pr.number}: {pr.title}")
        lines.append("")

    # Errors
    if state.errors:
        lines.append("## Errors")
        lines.append("")
        for err in state.errors:
            lines.append(f"- {err}")
        lines.append("")

    return "\n".join(lines)
