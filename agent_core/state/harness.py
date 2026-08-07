"""HarnessState: the continual harness H = (rho, G, K, M).

- rho (ρ) = BehaviorAddends — supplemental prompts
- G (gamma) = SubagentRegistry — sub-agent definitions
- K (kappa) = SkillRegistry — skills
- M (mu) = MemoryStore — memory

The base system prompt is immutable; only supplemental components change.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

from .behavior import BehaviorAddends
from .memory import MemoryStore
from .skills import SkillRegistry
from .subagents import SubagentRegistry


@dataclass
class HarnessSnapshot:
    snapshot_id: str
    timestamp: datetime
    prompts_state: dict  # addend id -> addend dict
    subagents_state: dict  # name -> definition dict
    skills_state: dict  # name -> path
    memory_keys: list[str]  # keys, not values

    def to_json_safe(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "prompts_state": self.prompts_state,
            "subagents_state": self.subagents_state,
            "skills_state": self.skills_state,
            "memory_keys": self.memory_keys,
        }

    @classmethod
    def from_json_safe(cls, data: dict) -> "HarnessSnapshot":
        return cls(
            snapshot_id=data["snapshot_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            prompts_state=data.get("prompts_state", {}),
            subagents_state=data.get("subagents_state", {}),
            skills_state=data.get("skills_state", {}),
            memory_keys=data.get("memory_keys", []),
        )


@dataclass
class HarnessState:
    """Continual Harness H = (rho, G, K, M). Each component is a
    VersionedState with CRUD and rollback."""

    prompts: BehaviorAddends  # rho
    subagents: SubagentRegistry  # G
    skills: SkillRegistry  # K
    memory: MemoryStore  # M

    def snapshot(self) -> HarnessSnapshot:
        """Create a before/after snapshot for refine."""
        return HarnessSnapshot(
            snapshot_id=uuid.uuid4().hex[:12],
            timestamp=datetime.now(),
            prompts_state={
                a.id: a.to_dict() for a in self.prompts.mirror_active()
            },
            subagents_state={
                name: asdict(defn)
                for name, defn in self.subagents.mirror_definitions().items()
            },
            skills_state={
                name: str(path) for name, path in self.skills.mirror_index().items()
            },
            memory_keys=sorted(self.memory.mirror_keys()),
        )

    def overview(self) -> str:
        """Human-readable summary of the current harness state."""
        snap = self.snapshot()
        lines = [
            f"# Harness overview ({snap.timestamp.isoformat()})",
            "",
            f"- prompts (rho): {len(snap.prompts_state)} active addends",
            f"- subagents (G): {', '.join(snap.subagents_state) or 'none'}",
            f"- skills (K): {', '.join(snap.skills_state) or 'none'}",
            f"- memory (M): {len(snap.memory_keys)} keys",
        ]
        return "\n".join(lines)
