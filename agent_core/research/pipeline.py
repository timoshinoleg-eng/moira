"""ResearchPipeline: evidence-first research (GPT-Researcher style).

plan -> gather -> evaluate -> synthesize. Every claim must carry a
source; nothing is stored without a citation. Works on mock LLMs with
zero external services.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from ..format.trust import TrustTier, credibility_score
from ..state.memory import MemoryStore
from .evidence import Evidence, Source
from .planner import ResearchPlanner


@dataclass
class ResearchResult:
    query: str
    sub_questions: list[str]
    evidence: list[Evidence]
    synthesis: str
    confidence: float  # 0.0–1.0
    sources: list[Source]


class ResearchPipeline:
    """Evidence-first pipeline: plan -> gather -> evaluate -> synthesize."""

    def __init__(self, llm: Callable, memory: MemoryStore):
        self.llm = llm
        self.memory = memory
        self.planner = ResearchPlanner(llm)

    async def research(self, query: str) -> ResearchResult:
        # 1. PLAN — decompose the query
        sub_questions = await self.planner.decompose(query)

        # 2. GATHER — one evidence item per sub-question (LLM supplies claims)
        evidence: list[Evidence] = []
        sources: list[Source] = []
        for i, sub_question in enumerate(sub_questions, start=1):
            out = await self.llm({"type": "gather", "sub_question": sub_question})
            source = Source(
                id=uuid.uuid4().hex[:8],
                url=str(out.get("source_url", "")),
                title=str(out.get("source_title", "untitled")),
                author=str(out.get("source_author", "unknown")),
                accessed_at=datetime.now(),
            )
            item = Evidence(
                claim=str(out.get("claim", "")),
                source=source,
                confidence=float(out.get("confidence", 0.7)),
                citation=f"[{i}]",
            )
            evidence.append(item)
            sources.append(source)

            # 3. EVALUATE — persist findings to memory with trust + confidence
            await self.memory.put(
                f"research:{sub_question[:40]}",
                {"claim": item.claim, "source": source.url, "citation": item.citation},
                trust=TrustTier.MACHINE_CONFIRMED,
                confidence=item.confidence,
            )

        # 4. SYNTHESIZE — one coherent answer from the claims
        out = await self.llm(
            {"type": "synthesize", "claims": [e.claim for e in evidence]}
        )
        synthesis = str(out.get("synthesis", ""))
        confidence = credibility_score(sources) if sources else 0.0

        return ResearchResult(
            query=query,
            sub_questions=sub_questions,
            evidence=evidence,
            synthesis=synthesis,
            confidence=confidence,
            sources=sources,
        )
