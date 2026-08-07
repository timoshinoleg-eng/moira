"""Central configuration for agent-core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .format.trust import TrustTier


@dataclass
class AgentCoreConfig:
    """Everything tunable in the framework with sane defaults."""

    db_path: str = ":memory:"
    skills_dir: str = "./skills"
    offload_dir: Optional[str] = None  # for ContextCompactor filesystem offload
    max_iterations: int = 10
    max_context_tokens: int = 8000
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    default_trust: TrustTier = TrustTier.UNVERIFIED
    subagent_idle_timeout: int = 1800  # 30 min (Prime Agent: drop after idle)
