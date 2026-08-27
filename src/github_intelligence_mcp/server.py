"""MCP server assembly and entry point.

Wires configuration, logging, the GitHub client lifecycle, and tool
registrations together. Domain logic never imports this module.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from mcp.server.mcpserver import MCPServer

from github_intelligence_mcp import __version__
from github_intelligence_mcp.config import Settings, load_settings
from github_intelligence_mcp.github.client import GitHubClient
from github_intelligence_mcp.logging import configure_logging
from github_intelligence_mcp.prompts import register_prompts
from github_intelligence_mcp.resources import register_resources
from github_intelligence_mcp.tools import register_all_tools

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

_SERVER_NAME = "GitHub Intelligence MCP"

_INSTRUCTIONS = """\
GitHub Intelligence provides structured, read-only access to GitHub
repository data through validated tools. Use get_repository to inspect a
repository's metadata before asking follow-up questions about its issues,
pull requests, commits, contributors, or releases. All outputs are structured
JSON derived deterministically from the GitHub REST API.
"""


def create_server(settings: Settings) -> MCPServer:
    """Build a fully wired MCP server instance (no network I/O performed).

    The GitHub client's connection pool is opened eagerly (construction does
    no I/O) and closed when the server shuts down via the lifespan hook.
    """
    configure_logging(settings.log_level)

    client = GitHubClient(settings)

    @asynccontextmanager
    async def _lifespan(_: MCPServer) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await client.aclose()

    server = MCPServer(
        name=_SERVER_NAME,
        version=__version__,
        instructions=_INSTRUCTIONS,
        lifespan=_lifespan,
    )
    register_all_tools(server, client)
    register_resources(server, client)
    register_prompts(server)
    return server


def main() -> None:
    """Entry point: load settings and run the MCP server over stdio."""
    server = create_server(load_settings())
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
