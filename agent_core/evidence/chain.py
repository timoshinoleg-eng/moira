"""EvidenceChain: ordered, rollbackable history of agent actions."""

from __future__ import annotations

from .record import EvidenceRecord


class EvidenceChain:
    """A chronological chain of EvidenceRecords.

    Supports point-in-time rollback: ``rollback_to(record_id)`` keeps the
    chain up to and including that record and returns the removed ones.
    """

    def __init__(self):
        self._records: list[EvidenceRecord] = []

    def add(self, record: EvidenceRecord) -> None:
        self._records.append(record)

    def get(self, record_id: str) -> EvidenceRecord | None:
        for r in self._records:
            if r.id == record_id:
                return r
        return None

    def all(self) -> list[EvidenceRecord]:
        return list(self._records)

    def rollback_to(self, record_id: str) -> list[EvidenceRecord]:
        """Roll the chain back to just after ``record_id``.

        Returns the records that were removed.
        """
        idx = next(
            (i for i, r in enumerate(self._records) if r.id == record_id), None
        )
        if idx is None:
            return []
        removed = self._records[idx + 1 :]
        self._records = self._records[: idx + 1]
        return removed

    def to_markdown(self) -> str:
        """Render the chain in OKF ``log.md`` format (chronological history)."""
        lines = ["# Evidence Log", ""]
        for r in self._records:
            lines.append(f"## {r.id}")
            lines.append(f"- **when**: {r.timestamp.isoformat()}")
            lines.append(f"- **who**: {r.actor}")
            lines.append(f"- **action**: {r.action}")
            lines.append(f"- **success**: {r.success}")
            if r.error:
                lines.append(f"- **error**: {r.error}")
            lines.append("")
        return "\n".join(lines)
