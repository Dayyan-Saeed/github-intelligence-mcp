"""MCP prompts for guided LLM interaction.

Prompts provide structured starting points that guide an LLM to use the
appropriate MCP tools for common investigation workflows. They contain no
GitHub API implementation — just well-crafted instructions and resource
references.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer


def register_prompts(server: MCPServer) -> None:
    """Register all MCP prompts on the server."""

    @server.prompt()
    def analyze_repository(owner: str, repo: str) -> list[dict[str, str]]:
        """Guide the LLM to produce a structured health analysis."""
        return [
            {
                "role": "user",
                "content": (
                    f"Analyze the health of GitHub repository '{owner}/{repo}'.\n\n"
                    "Steps:\n"
                    "1. Use `get_repository` to inspect basic metadata.\n"
                    "2. Use `analyze_repository` to compute the deterministic health "
                    "report with component scores and letter grade.\n"
                    "3. Use `find_maintenance_risks` to detect concrete maintenance "
                    "risks with severity and evidence.\n"
                    "4. Summarize findings: overall grade, strongest/weakest "
                    "components, and top 3 risks with recommended actions."
                ),
            }
        ]

    @server.prompt()
    def investigate_repository(owner: str, repo: str) -> list[dict[str, str]]:
        """Deep investigation workflow combining health, risks, and recent activity."""
        return [
            {
                "role": "user",
                "content": (
                    f"Investigate GitHub repository '{owner}/{repo}' comprehensively.\n\n"
                    "Steps:\n"
                    "1. Use `get_repository` for metadata overview.\n"
                    "2. Use `analyze_repository` for health scores.\n"
                    "3. Use `find_maintenance_risks` for risk detection.\n"
                    "4. Use `get_recent_commits` to review last 10 commits.\n"
                    "5. Use `get_issues` (open, limit 10) to spot patterns.\n"
                    "6. Use `get_pull_requests` (open, limit 10) to assess PR "
                    "hygiene.\n"
                    "7. Use `get_releases` to check release cadence.\n"
                    "8. Produce a structured report: metadata, health grade, "
                    "risk summary, commit patterns, issue/PR themes, and "
                    "release status."
                ),
            }
        ]

    @server.prompt()
    def review_maintenance_health(owner: str, repo: str) -> list[dict[str, str]]:
        """Focused maintenance health review with actionable recommendations."""
        return [
            {
                "role": "user",
                "content": (
                    f"Review the maintenance health of '{owner}/{repo}'.\n\n"
                    "Steps:\n"
                    "1. Use `analyze_repository` to get the health report.\n"
                    "2. Use `find_maintenance_risks` for risk detection.\n"
                    "3. For each risk with severity 'medium' or 'high', "
                    "suggest a concrete remediation step.\n"
                    "4. Rate overall maintenance posture: healthy, needs "
                    "attention, or at risk."
                ),
            }
        ]

    @server.prompt()
    def compare_repositories(
        owner_a: str, repo_a: str, owner_b: str, repo_b: str
    ) -> list[dict[str, str]]:
        """Side-by-side comparison of two repositories."""
        return [
            {
                "role": "user",
                "content": (
                    f"Compare '{owner_a}/{repo_a}' vs '{owner_b}/{repo_b}'.\n\n"
                    "Steps:\n"
                    "1. Use `compare_repositories` for a structured side-by-side "
                    "health comparison.\n"
                    "2. Use `find_maintenance_risks` on each repo to identify "
                    "differential risks.\n"
                    "3. Summarize: which repo is healthier overall, where each "
                    "excels, and which has fewer maintenance concerns."
                ),
            }
        ]

    @server.prompt()
    def summarize_recent_activity(owner: str, repo: str) -> list[dict[str, str]]:
        """Summarize recent development activity for a repository."""
        return [
            {
                "role": "user",
                "content": (
                    f"Summarize recent activity for '{owner}/{repo}'.\n\n"
                    "Steps:\n"
                    "1. Use `get_repository` for a quick metadata check.\n"
                    "2. Use `get_recent_commits` (limit 20) to review commit "
                    "patterns, frequency, and active contributors.\n"
                    "3. Use `get_releases` to check the latest release.\n"
                    "4. Use `get_issues` (open, limit 10) for current concerns.\n"
                    "5. Summarize: commit velocity, key contributors, latest "
                    "release, and open issues snapshot."
                ),
            }
        ]
