"""GitHub REST API client layer.

MCP-agnostic: knows nothing about tools, resources, prompts, or servers.
"""

from github_intelligence_mcp.github.client import GitHubClient, RateLimitInfo

__all__ = [
    "GitHubClient",
    "RateLimitInfo",
]
