"""MCP tool registrations.

Each module exposes ``register_*_tools``; this package aggregates them so the
server has a single registration entry point.
"""

from collections.abc import Callable

from mcp.server.mcpserver import MCPServer

from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.tools.contributors import register_contributor_tools
from github_intelligence_mcp.tools.releases import register_release_tools
from github_intelligence_mcp.tools.repositories import register_repository_tools


def register_all_tools(server: MCPServer, client: GitHubClient) -> None:
    """Register every MVP tool on the server."""
    registrars: list[Callable[[MCPServer, GitHubClient], None]] = [
        register_repository_tools,
        register_contributor_tools,
        register_release_tools,
    ]
    for registrar in registrars:
        registrar(server, client)
