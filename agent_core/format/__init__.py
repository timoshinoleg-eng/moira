"""Format package: OKF v0.2 knowledge bundles.

Keep bundle/concept imports lazy. State persistence imports frontmatter while
agent_core itself is still initialising; eagerly importing bundles there would
pull the research pipeline back into a partially initialised state package.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .frontmatter import parse_frontmatter, validate_frontmatter, write_frontmatter
from .trust import TrustTier, credibility_score

if TYPE_CHECKING:
    from .bundle import KnowledgeBundle
    from .concept import Concept


def __getattr__(name: str):
    if name == "KnowledgeBundle":
        from .bundle import KnowledgeBundle

        return KnowledgeBundle
    if name == "Concept":
        from .concept import Concept

        return Concept
    raise AttributeError(name)

__all__ = [
    "KnowledgeBundle",
    "Concept",
    "parse_frontmatter",
    "write_frontmatter",
    "validate_frontmatter",
    "TrustTier",
    "credibility_score",
]
