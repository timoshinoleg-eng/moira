"""Attention states: explicit modes of the agent's attention."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AttentionState(Enum):
    FOCUS = "focus"  # narrow task, one tool
    DIFFUSE = "diffuse"  # research, several sources
    IDLE = "idle"  # waiting for input/event
    WAITING = "waiting"  # waiting for permission/approval/answer (ccmux)


@dataclass
class AttentionTransition:
    from_state: AttentionState
    to_state: AttentionState
    reason: str
    timestamp: datetime
