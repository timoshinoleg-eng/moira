"""OKF v0.2 trust tiers and source credibility scoring."""

from __future__ import annotations

from enum import Enum


class TrustTier(Enum):
    """Trust level of a piece of knowledge."""

    UNVERIFIED = "unverified"
    MACHINE_CONFIRMED = "machine-confirmed"
    HUMAN_REVIEWED = "human-reviewed"


def credibility_score(sources: list) -> float:
    """0.0–1.0 credibility based on the number of sources.

    - 0 sources      -> 0.0
    - 1 source       -> 0.3
    - 2+ sources     -> 0.3 + 0.2 * (n - 1), capped at 0.9
    """
    n = len(sources or [])
    if n == 0:
        return 0.0
    if n == 1:
        return 0.3
    return min(0.9, 0.3 + 0.2 * (n - 1))
