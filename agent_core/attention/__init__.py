"""Attention package: explicit attention states."""

from .states import AttentionState, AttentionTransition
from .manager import AttentionManager

__all__ = ["AttentionState", "AttentionTransition", "AttentionManager"]
