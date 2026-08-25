"""Shared tool parameter annotations.

Centralizing ``Annotated`` parameter types keeps input schemas consistent
across tools and gives every list operation the same bounded limit contract
(spec: minimum 1, maximum 100).
"""

from typing import Annotated

from pydantic import Field

OwnerParam = Annotated[
    str,
    Field(
        min_length=1, max_length=100, description="Repository owner login (user or organization)."
    ),
]
RepoParam = Annotated[
    str,
    Field(min_length=1, max_length=100, description="Repository name."),
]
LimitParam = Annotated[int, Field(ge=1, le=100, description="Maximum number of items to return.")]

DEFAULT_LIMIT = 30
