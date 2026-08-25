"""Tests for input validation helpers."""

import pytest

from github_intelligence_mcp.errors import ValidationError
from github_intelligence_mcp.utils.validation import validate_owner, validate_repo


@pytest.mark.parametrize("value", ["facebook", "a", "A1", "user-name", "0" * 39])
def test_valid_owners(value: str) -> None:
    assert validate_owner(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "../etc/passwd",
        "a/b",
        "has space",
        "-leading",
        "trailing-",
        "double--hyphen",
        "a" * 40,
    ],
)
def test_invalid_owners(value: str) -> None:
    with pytest.raises(ValidationError):
        validate_owner(value)


@pytest.mark.parametrize("value", ["react", "my.repo_name", "repo-1.v2_x", "a" * 100])
def test_valid_repos(value: str) -> None:
    assert validate_repo(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "..",
        ".hidden",
        "-leading",
        "_leading",
        "a/b",
        "has space",
        "%20encoded",
        "a" * 101,
    ],
)
def test_invalid_repos(value: str) -> None:
    with pytest.raises(ValidationError):
        validate_repo(value)


def test_values_are_stripped() -> None:
    assert validate_owner("  facebook ") == "facebook"
    assert validate_repo(" react ") == "react"


def test_error_names_the_field() -> None:
    with pytest.raises(ValidationError, match="owner"):
        validate_owner("../bad", field="owner")
