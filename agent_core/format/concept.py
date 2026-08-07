"""OKF v0.2 Concept: one markdown file with YAML frontmatter."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..research.evidence import Source
from .frontmatter import parse_frontmatter, write_frontmatter
from .trust import TrustTier


@dataclass
class Concept:
    """A single OKF v0.2 knowledge concept (id == path without .md)."""

    id: str  # path without .md
    type: str  # REQUIRED in OKF
    title: str = ""
    description: str = ""
    resource: str = ""
    tags: list[str] = field(default_factory=list)
    body: str = ""

    # OKF trust/lifecycle fields
    trust: TrustTier = TrustTier.UNVERIFIED
    stale_after: Optional[str] = None  # ISO date
    sources: list[Source] = field(default_factory=list)
    generated_by: str = ""  # actor
    generated_at: str = ""  # ISO datetime
    verified_by: str = ""
    verified_at: str = ""

    def to_markdown(self) -> str:
        """Generate a .md file with YAML frontmatter."""
        meta = {
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "resource": self.resource,
            "tags": list(self.tags),
            "trust": self.trust.value,
            "stale_after": self.stale_after,
            "sources": [
                {
                    "id": s.id,
                    "url": s.url,
                    "title": s.title,
                    "author": s.author,
                    "accessed_at": s.accessed_at.isoformat(),
                    "usage_count": s.usage_count,
                }
                for s in self.sources
            ],
            "generated_by": self.generated_by,
            "generated_at": self.generated_at,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at,
        }
        # omit empty optional fields so the frontmatter stays clean
        meta = {k: v for k, v in meta.items() if v not in (None, "", [], {})}
        return write_frontmatter(meta, self.body)

    @classmethod
    def from_markdown(cls, content: str, concept_id: str) -> "Concept":
        """Parse a .md file (frontmatter + body) back into a Concept."""
        meta, body = parse_frontmatter(content)

        sources: list[Source] = []
        for s in meta.get("sources", []) or []:
            accessed_at = datetime.now()
            raw = s.get("accessed_at")
            if raw:
                try:
                    accessed_at = datetime.fromisoformat(str(raw))
                except ValueError:
                    pass
            sources.append(
                Source(
                    id=s.get("id") or uuid.uuid4().hex[:8],
                    url=s.get("url", ""),
                    title=s.get("title", ""),
                    author=s.get("author", ""),
                    accessed_at=accessed_at,
                    usage_count=int(s.get("usage_count", 0)),
                )
            )

        trust = TrustTier.UNVERIFIED
        try:
            trust = TrustTier(str(meta.get("trust", TrustTier.UNVERIFIED.value)))
        except ValueError:
            trust = TrustTier.UNVERIFIED

        return cls(
            id=concept_id,
            type=str(meta.get("type", "")),
            title=str(meta.get("title", "")),
            description=str(meta.get("description", "")),
            resource=str(meta.get("resource", "")),
            tags=list(meta.get("tags", []) or []),
            body=body,
            trust=trust,
            stale_after=meta.get("stale_after"),
            sources=sources,
            generated_by=str(meta.get("generated_by", "")),
            generated_at=str(meta.get("generated_at", "")),
            verified_by=str(meta.get("verified_by", "")),
            verified_at=str(meta.get("verified_at", "")),
        )
