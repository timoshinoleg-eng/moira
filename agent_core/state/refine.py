"""RefineEngine: the /refine mechanism (Prime Agent).

Analyses an evidence trajectory and applies evidence-backed updates to
the harness state (memory, prompts, skills, subagents). Every refine is
recorded with before/after snapshots and can be rolled back by id.
All changes are session-local by default; global scope requires an
explicit flag.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..evidence.record import EvidenceRecord
from ..format.trust import TrustTier
from .harness import HarnessSnapshot, HarnessState


@dataclass
class RefineResult:
    refine_id: str
    timestamp: datetime
    before: HarnessSnapshot
    after: HarnessSnapshot
    changes: list[dict]  # [{component, key, old, new, evidence_id}]
    scope: str  # "session" or "global"

    def to_json_safe(self) -> dict:
        return {
            "refine_id": self.refine_id,
            "timestamp": self.timestamp.isoformat(),
            "before": self.before.to_json_safe(),
            "after": self.after.to_json_safe(),
            "changes": self.changes,
            "scope": self.scope,
        }

    @classmethod
    def from_json_safe(cls, data: dict) -> "RefineResult":
        return cls(
            refine_id=data["refine_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            before=HarnessSnapshot.from_json_safe(data["before"]),
            after=HarnessSnapshot.from_json_safe(data["after"]),
            changes=data.get("changes", []),
            scope=data.get("scope", "session"),
        )


class RefineEngine:
    """Evidence-backed updates to harness state with snapshots + rollback."""

    def __init__(self, harness: HarnessState):
        self.harness = harness

    async def refine(
        self, trajectory: list[EvidenceRecord], *, scope: str = "session"
    ) -> RefineResult:
        """Analyse the trajectory and apply evidence-backed updates.

        Deterministic rules (no LLM needed):
        1. Every successful record -> memory entry ``evidence:<id>``
           with trust MACHINE_CONFIRMED and confidence 0.6.
        2. If any record failed -> a behavioral addend is registered
           warning against repeating the failed action (TTL 1 hour).
        """
        before = self.harness.snapshot()
        changes: list[dict] = []

        for record in trajectory:
            if not record.success:
                continue
            key = f"evidence:{record.id}"
            previous = await self.harness.memory.get(key)
            old = previous.value if previous else None
            summary = str(record.outputs) if record.outputs else record.action
            await self.harness.memory.put(
                key,
                {"action": record.action, "outputs": record.outputs, "summary": summary},
                trust=TrustTier.MACHINE_CONFIRMED,
                confidence=0.6,
                actor=record.actor,
                scope=scope,
            )
            changes.append(
                {
                    "component": "memory",
                    "key": key,
                    "old": old,
                    "new": summary,
                    "evidence_id": record.id,
                    "trust": TrustTier.MACHINE_CONFIRMED.value,
                    "confidence": 0.6,
                }
            )

        failures = [r for r in trajectory if not r.success]
        if failures:
            addend_text = "; ".join(
                f"{r.action} ({r.error or 'unknown error'})" for r in failures[:3]
            )
            addend_id = await self.harness.prompts.add(
                f"Avoid repeating failed actions: {addend_text}",
                ttl=3600,
                scope=scope,
                actor="agent",
            )
            changes.append(
                {
                    "component": "prompts",
                    "key": addend_id,
                    "old": None,
                    "new": addend_text,
                    "evidence_id": failures[0].id,
                }
            )

        after = self.harness.snapshot()
        result = RefineResult(
            refine_id=uuid.uuid4().hex[:12],
            timestamp=datetime.now(),
            before=before,
            after=after,
            changes=changes,
            scope=scope,
        )
        await self._store(result)
        return result

    async def rollback(self, snapshot_id: str) -> bool:
        """Roll back a refine by its id (reverts every recorded change)."""
        stored = await self._load(snapshot_id)
        if stored is None:
            return False
        for change in reversed(stored.changes):
            if change["component"] == "memory":
                if change.get("old") is None:
                    await self.harness.memory.delete(change["key"])
                else:
                    await self.harness.memory.put(
                        change["key"],
                        change["old"],
                        trust=TrustTier(change.get("trust", TrustTier.UNVERIFIED.value)),
                        confidence=float(change.get("confidence", 0.0)),
                        scope=stored.scope,
                    )
            elif change["component"] == "prompts":
                await self.harness.prompts.remove(change["key"])
        return True

    async def history(self) -> list[RefineResult]:
        """All refine operations, oldest first."""
        conn = await self.harness.memory._connect()
        await self._ensure_table(conn)
        cur = await conn.execute(
            "SELECT payload FROM refine_history ORDER BY timestamp ASC"
        )
        rows = await cur.fetchall()
        results = []
        for row in rows:
            import json

            results.append(RefineResult.from_json_safe(json.loads(row["payload"])))
        return results

    # ------------------------------------------------------------------ storage

    async def _store(self, result: RefineResult) -> None:
        import json

        conn = await self.harness.memory._connect()
        await self._ensure_table(conn)
        await conn.execute(
            "INSERT OR REPLACE INTO refine_history (refine_id, timestamp, payload) "
            "VALUES (?, ?, ?)",
            (result.refine_id, result.timestamp.isoformat(),
             json.dumps(result.to_json_safe(), ensure_ascii=False)),
        )
        await conn.commit()

    async def _load(self, refine_id: str) -> Optional[RefineResult]:
        import json

        conn = await self.harness.memory._connect()
        await self._ensure_table(conn)
        cur = await conn.execute(
            "SELECT payload FROM refine_history WHERE refine_id = ?", (refine_id,)
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return RefineResult.from_json_safe(json.loads(row["payload"]))

    async def _ensure_table(self, conn) -> None:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refine_history (
                refine_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        await conn.commit()
