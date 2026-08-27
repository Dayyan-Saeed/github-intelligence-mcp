"""MCP resources for structured repository data exposure.

Resources provide read-only access to repository data via URI templates.
They do not duplicate large payloads — each resource returns a focused,
structured summary suitable for LLM context windows.
"""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.github.commits import get_recent_commits
from github_intelligence_mcp.github.contributors import get_contributors
from github_intelligence_mcp.github.issues import get_issues
from github_intelligence_mcp.github.pull_requests import get_pull_requests
from github_intelligence_mcp.github.releases import get_releases
from github_intelligence_mcp.github.repositories import get_repository
from github_intelligence_mcp.logging import get_logger
from github_intelligence_mcp.tools._guard import guarded_tool_call

_log = get_logger(__name__)


def _serialize(obj: object) -> str:
    """Serialize a Pydantic model or list of models to JSON."""
    if hasattr(obj, "model_dump_json"):
        result = obj.model_dump_json(indent=2)
        return str(result)
    if isinstance(obj, list) and obj and hasattr(obj[0], "model_dump"):
        items = [i.model_dump(mode="json") for i in obj]
        return json.dumps(items, indent=2)
    return json.dumps(obj, default=str, indent=2)


def register_resources(server: MCPServer, client: GitHubClient) -> None:
    """Register all MCP resources on the server."""

    @server.resource("github://repo/{owner}/{repo}")
    async def repo_resource(owner: str, repo: str) -> str:
        """Repository metadata: description, stars, forks, language, license."""
        result = await guarded_tool_call(
            lambda: get_repository(client, owner, repo),
            tool="resource:repo",
            owner=owner,
            repo=repo,
            not_found_message=f"Repository '{owner}/{repo}' was not found.",
        )
        return _serialize(result)

    @server.resource("github://repo/{owner}/{repo}/issues")
    async def issues_resource(owner: str, repo: str) -> str:
        """Open issues with labels, authors, and creation dates."""
        result = await guarded_tool_call(
            lambda: get_issues(client, owner, repo, state="open", limit=30),
            tool="resource:issues",
            owner=owner,
            repo=repo,
            not_found_message=f"Repository '{owner}/{repo}' was not found.",
        )
        return _serialize(result)

    @server.resource("github://repo/{owner}/{repo}/pulls")
    async def pulls_resource(owner: str, repo: str) -> str:
        """Open pull requests with authors, branches, and timestamps."""
        result = await guarded_tool_call(
            lambda: get_pull_requests(client, owner, repo, state="open", limit=30),
            tool="resource:pulls",
            owner=owner,
            repo=repo,
            not_found_message=f"Repository '{owner}/{repo}' was not found.",
        )
        return _serialize(result)

    @server.resource("github://repo/{owner}/{repo}/commits")
    async def commits_resource(owner: str, repo: str) -> str:
        """Recent commits with authors, messages, and dates."""
        result = await guarded_tool_call(
            lambda: get_recent_commits(client, owner, repo, limit=30),
            tool="resource:commits",
            owner=owner,
            repo=repo,
            not_found_message=f"Repository '{owner}/{repo}' was not found.",
        )
        return _serialize(result)

    @server.resource("github://repo/{owner}/{repo}/contributors")
    async def contributors_resource(owner: str, repo: str) -> str:
        """Top contributors by commit count with avatar and profile links."""
        result = await guarded_tool_call(
            lambda: get_contributors(client, owner, repo, limit=30),
            tool="resource:contributors",
            owner=owner,
            repo=repo,
            not_found_message=f"Repository '{owner}/{repo}' was not found.",
        )
        return _serialize(result)

    @server.resource("github://repo/{owner}/{repo}/releases")
    async def releases_resource(owner: str, repo: str) -> str:
        """Recent releases with versions, dates, and asset counts."""
        result = await guarded_tool_call(
            lambda: get_releases(client, owner, repo, limit=10),
            tool="resource:releases",
            owner=owner,
            repo=repo,
            not_found_message=f"Repository '{owner}/{repo}' was not found.",
        )
        return _serialize(result)
