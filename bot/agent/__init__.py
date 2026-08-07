"""agent_core wiring layer for Moira.

Initializes a HarnessState (H = ρ, G, K, M) and exposes it as a singleton
that the rest of the bot can import. The harness gives Moira:
  - versioned memory with confidence and TTL (replaces raw SQL _recent_reads_memory)
  - behavior addends (supplemental prompts, versioned, persist_to_disk)
  - evidence chain (replaces _log_usage with a rollback-capable audit trail)
  - attention manager (focus/diffuse/idle/waiting observability)
  - retry policy with circuit breaker (replaces manual for-loop retry)

Design: the harness lives in-process and uses SQLite (:memory: by default).
It does NOT replace the main PostgreSQL/SQLite application DB — it augments
the LLM layer with structured, observable, versioned state.
"""

from __future__ import annotations

import logging
from typing import Optional

from agent_core import (
    AttentionManager,
    BehaviorAddends,
    EvidenceChain,
    HarnessState,
    MemoryStore,
    SkillRegistry,
    SubagentRegistry,
)

logger = logging.getLogger(__name__)

# Singleton — initialized once on startup
_harness: Optional[HarnessState] = None
_attention: Optional[AttentionManager] = None
_evidence: Optional[EvidenceChain] = None


async def init_harness(skills_dir: str = ".agent_state/skills") -> HarnessState:
    """Initialize the singleton HarnessState. Call once on bot startup.

    Uses in-memory SQLite — the harness state is ephemeral by default.
    For persistent harness state across restarts, pass a file path.
    """
    global _harness, _attention, _evidence

    memory = MemoryStore(":memory:")
    prompts = BehaviorAddends(":memory:")
    skills = SkillRegistry(skills_dir)
    subagents = SubagentRegistry(":memory:")

    _harness = HarnessState(
        prompts=prompts,
        subagents=subagents,
        skills=skills,
        memory=memory,
    )
    _attention = AttentionManager()
    _evidence = EvidenceChain()

    # Seed Moira's voice/rule prompts as behavior addends (session scope)
    from ..llm.adapter import VOICE_RU, VOICE_EN, FORMAT_RU, FORMAT_EN

    # ttl=86400*365 = 1 year (effectively no expiry for session-scoped prompts)
    _FOREVER = 86400 * 365

    await _harness.prompts.add(
        f"[voice:ru] {VOICE_RU}",
        ttl=_FOREVER,
        scope="session",
        actor="system",
    )
    await _harness.prompts.add(
        f"[voice:en] {VOICE_EN}",
        ttl=_FOREVER,
        scope="session",
        actor="system",
    )
    await _harness.prompts.add(
        f"[format:ru] {FORMAT_RU}",
        ttl=_FOREVER,
        scope="session",
        actor="system",
    )
    await _harness.prompts.add(
        f"[format:en] {FORMAT_EN}",
        ttl=_FOREVER,
        scope="session",
        actor="system",
    )

    logger.info("HarnessState initialized: H=(ρ,G,K,M) with %d prompts seeded", 4)
    return _harness


def get_harness() -> HarnessState:
    """Get the singleton harness. Must call init_harness() first."""
    if _harness is None:
        raise RuntimeError("HarnessState not initialized — call init_harness() on startup")
    return _harness


def get_attention() -> AttentionManager:
    """Get the singleton AttentionManager."""
    if _attention is None:
        raise RuntimeError("AttentionManager not initialized — call init_harness() on startup")
    return _attention


def get_evidence() -> EvidenceChain:
    """Get the singleton EvidenceChain."""
    if _evidence is None:
        raise RuntimeError("EvidenceChain not initialized — call init_harness() on startup")
    return _evidence


async def close_harness() -> None:
    """Close all DB connections on shutdown."""
    global _harness, _attention, _evidence
    from agent_core.state.base import close_all_connections
    await close_all_connections()
    _harness = None
    _attention = None
    _evidence = None
    logger.info("HarnessState closed")
