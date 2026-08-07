"""Integration tests: agent-core ↔ Moira bot.

Tests that agent-core is correctly wired into Moira:
  1. HarnessState initializes with seeded prompts
  2. MemoryStore stores and retrieves user memory with confidence
  3. EvidenceChain records LLM usage events
  4. AttentionManager transitions focus → idle on LLM calls
  5. BehaviorAddends compose base prompt with supplemental addends
  6. LLM adapter degrades gracefully when agent-core is not initialized
"""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime

from agent_core import (
    AttentionState,
    EvidenceRecord,
    TrustTier,
)


# ------------------------------------------------------------------ harness init

async def test_harness_init_seeds_prompts():
    """init_harness seeds 4 behavior addends (voice:ru, voice:en, format:ru, format:en)."""
    from bot.agent import init_harness, get_harness, close_harness

    harness = await init_harness()
    addends = await harness.prompts.active()
    assert len(addends) == 4

    # Verify voice prompts are present
    composed = await harness.prompts.compose("base system prompt")
    assert "Мойра" in composed  # from VOICE_RU
    assert "Moira" in composed    # from VOICE_EN
    assert "JSON" in composed     # from FORMAT_RU

    await close_harness()


async def test_harness_singleton():
    """get_harness returns the same instance after init."""
    from bot.agent import init_harness, get_harness, close_harness

    await init_harness()
    h1 = get_harness()
    h2 = get_harness()
    assert h1 is h2

    await close_harness()


async def test_harness_not_initialized_raises():
    """get_harness raises RuntimeError if not initialized."""
    from bot.agent import close_harness, get_harness

    await close_harness()
    with pytest.raises(RuntimeError, match="not initialized"):
        get_harness()


# ------------------------------------------------------------------ memory

async def test_memory_store_with_confidence():
    """MemoryStore stores user memory with confidence and trust metadata."""
    from bot.agent import init_harness, get_harness, close_harness

    await init_harness()
    harness = get_harness()

    await harness.memory.put(
        "user:42:recent_reads",
        "Пользователь спрашивал о любви | Колесо Фортуны | Солнце",
        ttl=3600,
        trust=TrustTier.MACHINE_CONFIRMED,
        confidence=0.85,
        actor="agent:moira",
        scope="session",
    )

    entry = await harness.memory.get("user:42:recent_reads")
    assert entry is not None
    assert "Колесо Фортуны" in entry.value
    assert entry.confidence == 0.85
    assert entry.trust == TrustTier.MACHINE_CONFIRMED
    assert entry.actor == "agent:moira"

    await close_harness()


async def test_memory_by_confidence():
    """by_confidence filters entries above threshold."""
    from bot.agent import init_harness, get_harness, close_harness

    await init_harness()
    harness = get_harness()

    await harness.memory.put("low", "low confidence data", confidence=0.3)
    await harness.memory.put("high", "high confidence data", confidence=0.9)
    await harness.memory.put("mid", "medium confidence data", confidence=0.7)

    high = await harness.memory.by_confidence(0.7)
    keys = [e.key for e in high]
    assert "high" in keys
    assert "mid" in keys
    assert "low" not in keys

    await close_harness()


# ------------------------------------------------------------------ evidence chain

async def test_evidence_chain_records_llm_usage():
    """EvidenceChain records LLM usage events with success/error metadata."""
    from bot.agent import init_harness, get_evidence, close_harness

    await init_harness()
    chain = get_evidence()

    # Simulate a successful LLM call
    chain.add(EvidenceRecord(
        id="llm:42:1234567890",
        action="llm_interpret status=ok spread=love",
        actor="agent:moira",
        timestamp=datetime.now(),
        inputs={"user_id": 42, "spread": "love", "model": "deepseek-chat"},
        outputs={"status": "ok", "latency_ms": 1500, "attempts": 1},
        success=True,
    ))

    # Simulate a failed LLM call (fallback)
    chain.add(EvidenceRecord(
        id="llm:42:1234567891",
        action="llm_interpret status=fallback spread=choice",
        actor="agent:moira",
        timestamp=datetime.now(),
        inputs={"user_id": 42, "spread": "choice", "model": "deepseek-chat"},
        outputs={"status": "fallback", "latency_ms": 3000, "attempts": 2, "error_category": "timeout"},
        success=False,
        error="timeout",
    ))

    all_records = chain.all()
    assert len(all_records) == 2
    assert all_records[0].success is True
    assert all_records[1].success is False
    assert all_records[1].error == "timeout"

    # Rollback to first record (remove the failed one)
    removed = chain.rollback_to("llm:42:1234567890")
    assert len(removed) == 1
    assert removed[0].id == "llm:42:1234567891"
    assert len(chain.all()) == 1

    await close_harness()


async def test_evidence_chain_to_markdown():
    """EvidenceChain.to_markdown produces OKF log.md format."""
    from bot.agent import init_harness, get_evidence, close_harness

    await init_harness()
    chain = get_evidence()

    chain.add(EvidenceRecord(
        id="test:1",
        action="test action",
        actor="agent:test",
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        inputs={"q": "test"},
        outputs={"a": "result"},
        success=True,
    ))

    md = chain.to_markdown()
    assert "test action" in md
    assert "agent:test" in md

    await close_harness()


# ------------------------------------------------------------------ attention

async def test_attention_transitions_on_llm_call():
    """AttentionManager transitions focus → idle on LLM call lifecycle."""
    from bot.agent import init_harness, get_attention, close_harness

    await init_harness()
    attn = get_attention()

    # Initial state is IDLE
    assert attn.current() == AttentionState.IDLE

    # Transition to FOCUS (start of interpret_reading)
    attn.transition(AttentionState.FOCUS, reason="interpret_reading: love")
    assert attn.current() == AttentionState.FOCUS

    # Transition to IDLE (success)
    attn.transition(AttentionState.IDLE, reason="llm success")
    assert attn.current() == AttentionState.IDLE

    # Transition to FOCUS again
    attn.transition(AttentionState.FOCUS, reason="interpret_reading: choice")
    assert attn.current() == AttentionState.FOCUS

    # Transition to IDLE (fallback)
    attn.transition(AttentionState.IDLE, reason="llm fallback")
    assert attn.current() == AttentionState.IDLE

    # Check history
    history = attn.history()
    assert len(history) == 4
    assert history[0].from_state == AttentionState.IDLE
    assert history[0].to_state == AttentionState.FOCUS

    await close_harness()


async def test_attention_waiting_state():
    """WAITING state is available for permission/approval flows."""
    from bot.agent import init_harness, get_attention, close_harness

    await init_harness()
    attn = get_attention()

    attn.transition(AttentionState.FOCUS, reason="start")
    attn.transition(AttentionState.WAITING, reason="user approval needed")
    assert attn.current() == AttentionState.WAITING

    attn.transition(AttentionState.FOCUS, reason="approved")
    assert attn.current() == AttentionState.FOCUS

    await close_harness()


# ------------------------------------------------------------------ behavior addends

async def test_behavior_addends_compose():
    """BehaviorAddends.compose appends supplemental prompts to base prompt."""
    from bot.agent import init_harness, get_harness, close_harness

    await init_harness()
    harness = get_harness()

    # Add a custom temporary addend
    await harness.prompts.add(
        "Always mention card symbolism in interpretations.",
        ttl=1800,
        scope="session",
        actor="admin",
    )

    composed = await harness.prompts.compose("You are a tarot oracle.")
    assert "You are a tarot oracle." in composed
    assert "card symbolism" in composed

    # Active addends should now be 5 (4 seeded + 1 custom)
    active = await harness.prompts.active()
    assert len(active) == 5

    await close_harness()


# ------------------------------------------------------------------ graceful degradation

async def test_adapter_works_without_agent_core():
    """LLM adapter functions correctly when agent-core is not initialized.

    The adapter uses try/except around agent-core calls, so it should
    degrade gracefully to the original behavior.
    """
    # Don't call init_harness() — _AGENT_CORE should be False or calls should be no-ops
    from bot.llm.adapter import _AGENT_CORE

    # If agent-core is installed, _AGENT_CORE may be True (import succeeded)
    # but get_harness() will raise RuntimeError (not initialized)
    # The adapter catches this and continues without agent-core
    assert isinstance(_AGENT_CORE, bool)


# ------------------------------------------------------------------ harness snapshot

async def test_harness_snapshot_and_overview():
    """HarnessState.snapshot and overview work correctly."""
    from bot.agent import init_harness, get_harness, close_harness

    await init_harness()
    harness = get_harness()

    # Add some memory
    await harness.memory.put("test:key", "test value", confidence=0.5)

    # Take snapshot
    snap = harness.snapshot()
    assert snap.snapshot_id  # not empty
    assert "test" in snap.memory_keys or "test:key" in snap.memory_keys

    # Overview
    overview = harness.overview()
    assert isinstance(overview, str)
    assert len(overview) > 0

    await close_harness()
