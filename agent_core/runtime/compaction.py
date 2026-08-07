"""ContextCompactor: context summarization + filesystem offloading (DeerFlow).

When the message history exceeds ``max_tokens``, the oldest messages
are collapsed into a single summary message. Intermediate payloads can
be offloaded to disk; the summary keeps a reference to the offloaded
file.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Callable, Optional


class ContextCompactor:
    """Aggressive strategy:

    1. Old messages -> summary (via LLM, or a deterministic fallback)
    2. Intermediates -> filesystem (offload_dir), if set
    3. The summary replaces N old messages with one
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        llm: Optional[Callable] = None,
        offload_dir: Optional[str] = None,
    ):
        self.max_tokens = max_tokens
        self.llm = llm
        self.offload_dir = offload_dir

    def estimate_tokens(self, text: str) -> int:
        """Rough estimate: len(text) // 4."""
        return len(text) // 4

    def needs_compaction(self, messages: list[dict]) -> bool:
        total = sum(
            self.estimate_tokens(str(m.get("content", ""))) for m in messages
        )
        return total > self.max_tokens

    async def compact(self, messages: list[dict]) -> list[dict]:
        if not self.needs_compaction(messages):
            return list(messages)
        if not messages:
            return []

        n = max(1, len(messages) // 2)
        old, rest = messages[:n], messages[n:]
        summary = await self._summarize(old)

        summary_message: dict[str, Any] = {
            "role": "system",
            "content": f"Summary of previous conversation: {summary}",
        }
        if self.offload_dir:
            target = os.path.join(
                self.offload_dir, f"offload-{uuid.uuid4().hex[:8]}.jsonl"
            )
            path = await self.offload(old, target)
            summary_message["offloaded_to"] = path

        return [summary_message] + rest

    async def _summarize(self, messages: list[dict]) -> str:
        if self.llm is not None:
            out = await self.llm({"type": "summarize", "messages": messages})
            summary = out.get("summary")
            if summary:
                return str(summary)
        # deterministic fallback (no LLM): squeeze the tail of the window
        parts = []
        for m in messages[-5:]:
            content = str(m.get("content", ""))[:200]
            parts.append(f"{m.get('role', '?')}: {content}")
        return "Previously discussed: " + " | ".join(parts)

    async def offload(self, messages: list[dict], path: str) -> str:
        """Write intermediates to disk (JSON Lines); return the path."""
        path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for m in messages:
                fh.write(json.dumps(m, ensure_ascii=False) + "\n")
        return path
