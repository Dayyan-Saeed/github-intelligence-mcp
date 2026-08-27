"""Tests for MCP prompts."""

from mcp.types import GetPromptResult

from github_intelligence_mcp.server import create_server


async def test_all_prompts_registered(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    prompts = await server.list_prompts()
    names = {p.name for p in prompts}
    expected = {
        "analyze_repository",
        "investigate_repository",
        "review_maintenance_health",
        "compare_repositories",
        "summarize_recent_activity",
    }
    assert expected == names


async def test_analyze_repository_prompt(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    result = await server.get_prompt("analyze_repository", {"owner": "o", "repo": "r"})
    assert isinstance(result, GetPromptResult)
    assert len(result.messages) >= 1
    content = result.messages[0].content
    text = content.text if hasattr(content, "text") else str(content)
    assert "analyze_repository" in text
    assert "find_maintenance_risks" in text


async def test_compare_repositories_prompt(settings) -> None:  # type: ignore[no-untyped-def]
    server = create_server(settings)
    result = await server.get_prompt(
        "compare_repositories",
        {"owner_a": "o", "repo_a": "r", "owner_b": "o", "repo_b": "r"},
    )
    assert isinstance(result, GetPromptResult)
    content = result.messages[0].content
    text = content.text if hasattr(content, "text") else str(content)
    assert "compare_repositories" in text
