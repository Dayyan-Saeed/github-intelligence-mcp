"""Tests for client cache integration."""

import httpx
import respx
from pydantic import SecretStr

from github_intelligence_mcp.cache import MemoryCache
from github_intelligence_mcp.config import Settings
from github_intelligence_mcp.github.client import GitHubClient

_SETTINGS_KWARGS: dict[str, object] = {
    "github_token": SecretStr("ghp_test123"),
    "log_level": "ERROR",
}


@respx.mock
async def test_client_caches_get_json(mock_github) -> None:  # type: ignore[no-untyped-def]
    cache = MemoryCache()
    client = GitHubClient(Settings(**_SETTINGS_KWARGS), cache=cache)  # type: ignore[arg-type]

    respx.get("https://api.github.com/repos/o/r").mock(
        return_value=httpx.Response(200, json={"full_name": "o/r"})
    )

    result1 = await client.get_json("/repos/o/r")
    result2 = await client.get_json("/repos/o/r")

    assert result1 == result2
    assert cache.get("/repos/o/r") is not None
    await client.aclose()


@respx.mock
async def test_client_bypasses_cache_for_non_repo_paths(mock_github) -> None:  # type: ignore[no-untyped-def]
    cache = MemoryCache()
    client = GitHubClient(Settings(**_SETTINGS_KWARGS), cache=cache)  # type: ignore[arg-type]

    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(200, json={"login": "u"})
    )

    await client.get_json("/user")
    assert cache.get("/user") is None
    await client.aclose()


@respx.mock
async def test_client_respects_ttl_per_endpoint(mock_github) -> None:  # type: ignore[no-untyped-def]
    cache = MemoryCache()
    client = GitHubClient(Settings(**_SETTINGS_KWARGS), cache=cache)  # type: ignore[arg-type]

    respx.get("https://api.github.com/repos/o/r/commits").mock(
        return_value=httpx.Response(200, json=[{"sha": "abc"}])
    )

    await client.get_json("/repos/o/r/commits")
    assert cache.get("/repos/o/r/commits") is not None

    respx.get("https://api.github.com/repos/o/r/issues").mock(
        return_value=httpx.Response(200, json=[])
    )

    await client.get_json("/repos/o/r/issues")
    assert cache.get("/repos/o/r/issues") is not None

    await client.aclose()


def test_ttl_mapping() -> None:
    assert GitHubClient._ttl_for_path("/repos/o/r") == 600
    assert GitHubClient._ttl_for_path("/repos/o/r/issues") == 300
    assert GitHubClient._ttl_for_path("/repos/o/r/pulls") == 300
    assert GitHubClient._ttl_for_path("/repos/o/r/commits") == 120
    assert GitHubClient._ttl_for_path("/repos/o/r/contributors") == 600
    assert GitHubClient._ttl_for_path("/repos/o/r/releases") == 600
    assert GitHubClient._ttl_for_path("/user") == 0
