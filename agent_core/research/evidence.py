"""Source + Evidence dataclasses for the research pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Source:
    """One consulted information source."""

    id: str
    url: str
    title: str
    author: str
    accessed_at: datetime
    usage_count: int = 0


@dataclass
class Evidence:
    """A claim backed by a specific source."""

    claim: str
    source: Source
    confidence: float  # 0.0–1.0
    citation: str  # footnote-style
