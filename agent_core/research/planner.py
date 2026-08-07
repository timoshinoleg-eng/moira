"""ResearchPlanner: decompose a query into sub-questions and rank sources."""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

from .evidence import Source


class ResearchPlanner:
    """Decomposes a research query into sub-questions.

    With an LLM: ``llm({"type": "decompose", "query": q})`` must return
    ``{"sub_questions": [...]}``. Without one, a deterministic heuristic
    splits the query on conjunctions and sentence boundaries.
    """

    def __init__(self, llm: Optional[Callable] = None):
        self.llm = llm

    async def decompose(self, query: str) -> list[str]:
        if self.llm is not None:
            out = await self.llm({"type": "decompose", "query": query})
            sub_questions = out.get("sub_questions") or []
            return [str(s) for s in sub_questions]
        return self._heuristic_split(query)

    def _heuristic_split(self, query: str) -> list[str]:
        cleaned = query.strip().rstrip("?.! ")
        parts = re.split(r"\s+(?:и|and|,)\s+|[.?!]\s+", cleaned)
        result = [p.strip() for p in parts if p.strip()]
        return result[:3] or [query]

    async def select_sources(
        self, sub_question: str, available: list[Source]
    ) -> list[Source]:
        """Rank sources by word overlap with the sub-question, then by usage."""
        q_words = set(re.findall(r"[a-zа-яё0-9]+", sub_question.lower()))
        scored: list[tuple[int, int, Source]] = []
        for source in available:
            haystack = f"{source.title} {source.url}".lower()
            overlap = len(q_words & set(re.findall(r"[a-zа-яё0-9]+", haystack)))
            scored.append((overlap, source.usage_count, source))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [s for _, _, s in scored]
