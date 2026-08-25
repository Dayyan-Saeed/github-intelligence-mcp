"""Documentation score (weight: 10%).

Cheap-to-verify documentation signals available from repository metadata
and a README existence check. Presence-based by design: this component
measures discoverability of docs, not their quality.
"""

from __future__ import annotations

from typing import Any

from github_intelligence_mcp.analysis.scoring import mean

WEIGHT = 0.10
LABEL = "Documentation"

_README_POINTS = 50
_LICENSE_POINTS = 25
_DESCRIPTION_POINTS = 15
_HOMEPAGE_POINTS = 10


def compute_documentation_score(
    *,
    has_readme: bool,
    has_license: bool,
    has_description: bool,
    has_homepage: bool,
) -> tuple[int, dict[str, Any]]:
    """Score documented-ness from four boolean presence signals."""
    points = sum(
        (
            _README_POINTS * has_readme,
            _LICENSE_POINTS * has_license,
            _DESCRIPTION_POINTS * has_description,
            _HOMEPAGE_POINTS * has_homepage,
        )
    )
    details: dict[str, Any] = {
        "has_readme": has_readme,
        "has_license": has_license,
        "has_description": has_description,
        "has_homepage": has_homepage,
        "points_earned": points,
        "points_possible": 100,
    }
    return mean([round(points)]), details
