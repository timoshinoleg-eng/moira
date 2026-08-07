"""AttentionManager: explicit attention-state transitions + heuristics."""

from __future__ import annotations

import re
from datetime import datetime

from .states import AttentionState, AttentionTransition

# Concrete action verbs -> FOCUS
_FOCUS_VERBS = {
    "create", "write", "build", "fix", "run", "make", "implement", "solve",
    "refactor", "test", "deploy", "compile",
    "создай", "напиши", "собери", "запусти", "сделай", "построй", "почини",
    "исправь", "реализуй", "напиши", "установи", "сохрани",
}

# Research-flavoured words -> DIFFUSE
_DIFFUSE_MARKERS = {
    "research", "investigate", "explore", "analyze", "compare", "survey",
    "review", "summarize", "understand",
    "исследуй", "изучи", "сравни", "проанализируй", "обзор", "разбери",
    "изучение", "исследование",
}

# Approval/question markers -> WAITING
_WAIT_MARKERS = {
    "approve", "confirm", "permission", "approval", "ask", "question",
    "подтверди", "одобри", "разреши", "спроси", "уточни",
}


class AttentionManager:
    """Tracks the current attention state and every transition."""

    def __init__(self):
        self._current = AttentionState.IDLE
        self._history: list[AttentionTransition] = []

    def current(self) -> AttentionState:
        return self._current

    def transition(self, to: AttentionState, reason: str) -> AttentionTransition:
        transition = AttentionTransition(
            from_state=self._current,
            to_state=to,
            reason=reason,
            timestamp=datetime.now(),
        )
        self._history.append(transition)
        self._current = to
        return transition

    def history(self) -> list[AttentionTransition]:
        return list(self._history)

    # ----------------------------------------------------------------- heuristics

    def should_focus(self, task: str) -> bool:
        """If the task contains a concrete action verb -> focus."""
        words = set(re.findall(r"[a-zа-яё0-9-]+", task.lower()))
        return bool(words & _FOCUS_VERBS)

    def should_wait(self, task: str) -> bool:
        """If the task asks for confirmation/approval -> waiting."""
        low = task.lower().strip()
        return bool(
            any(m in low for m in _WAIT_MARKERS)
            or low.rstrip().endswith("?")
        )

    def should_diffuse(self, task: str) -> bool:
        """If the task is research-flavoured -> diffuse."""
        words = set(re.findall(r"[a-zа-яё0-9-]+", task.lower()))
        return bool(words & _DIFFUSE_MARKERS)
