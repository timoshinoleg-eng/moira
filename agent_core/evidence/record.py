"""EvidenceRecord: one auditable agent action."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class EvidenceRecord:
    """What was done, by whom, when, with which inputs/outputs."""

    id: str
    action: str  # what was done
    actor: str  # who did it ("agent:...", "human:...", "process:...")
    timestamp: datetime
    inputs: dict  # what was on the input
    outputs: dict  # what came out
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "actor": self.actor,
            "timestamp": self.timestamp.isoformat(),
            "inputs": self.inputs,
            "outputs": self.outputs,
            "success": self.success,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRecord":
        return cls(
            id=data["id"],
            action=data["action"],
            actor=data["actor"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            success=data.get("success", True),
            error=data.get("error"),
        )
