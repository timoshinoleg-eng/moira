"""BehaviorAddends: supplemental prompts (rho in HarnessState).

They live for a TTL and are removed automatically. The base system
prompt stays immutable (Prime Agent) — only supplemental addends are
composed on top of it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from ..format.frontmatter import write_frontmatter
from .base import SQLiteVersionedState, VersionEntry, _from_json, _iso, _parse_iso, _to_json


@dataclass
class BehaviorAddend:
    id: str
    text: str
    ttl: int
    created_at: datetime
    scope: str  # "session" or "global"
    actor: str
    expires_at: datetime

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "ttl": self.ttl,
            "created_at": _iso(self.created_at),
            "scope": self.scope,
            "actor": self.actor,
            "expires_at": _iso(self.expires_at),
        }


class BehaviorAddends(SQLiteVersionedState):
    """Supplemental prompt store with TTL expiry and journaled rollback."""

    def __init__(self, db_path: str = ":memory:"):
        super().__init__(db_path)
        self._mirror: dict[str, BehaviorAddend] = {}

    async def _connect(self) -> Any:
        conn = await super()._connect()
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS behavior_addends (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                ttl INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                scope TEXT NOT NULL,
                actor TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS behavior_journal (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                op TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL
            )
            """
        )
        await conn.commit()
        cur = await conn.execute("SELECT * FROM behavior_addends")
        self._mirror = {r["id"]: self._row_to_addend(r) for r in await cur.fetchall()}
        return conn

    # ------------------------------------------------------------------ core API

    async def add(
        self,
        addend: str,
        *,
        ttl: int = 3600,
        scope: str = "session",
        actor: str = "agent",
    ) -> str:
        """Add a supplemental prompt; returns its id."""
        conn = await self._connect()
        addend_id = uuid.uuid4().hex[:12]
        created = datetime.now()
        expires = created + timedelta(seconds=ttl)
        addend_obj = BehaviorAddend(
            id=addend_id, text=addend, ttl=ttl, created_at=created,
            scope=scope, actor=actor, expires_at=expires,
        )
        await conn.execute(
            "INSERT INTO behavior_addends (id, text, ttl, created_at, scope, actor, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (addend_id, addend, ttl, _iso(created), scope, actor, _iso(expires)),
        )
        await conn.execute(
            "INSERT INTO behavior_journal (op, payload, timestamp, actor) VALUES ('add', ?, ?, ?)",
            (addend_id, _iso(created), actor),
        )
        await conn.commit()
        self._mirror[addend_id] = addend_obj
        return addend_id

    async def remove(self, addend_id: str) -> bool:
        conn = await self._connect()
        cur = await conn.execute(
            "SELECT * FROM behavior_addends WHERE id = ?", (addend_id,)
        )
        row = await cur.fetchone()
        if row is None:
            return False
        payload = _to_json(dict(row))
        await conn.execute("DELETE FROM behavior_addends WHERE id = ?", (addend_id,))
        await conn.execute(
            "INSERT INTO behavior_journal (op, payload, timestamp, actor) "
            "VALUES ('remove', ?, ?, ?)",
            (payload, _iso(), row["actor"]),
        )
        await conn.commit()
        self._mirror.pop(addend_id, None)
        return True

    async def active(self) -> list[BehaviorAddend]:
        """Non-expired addends, oldest first (SQLite-backed)."""
        conn = await self._connect()
        cur = await conn.execute(
            "SELECT * FROM behavior_addends WHERE expires_at > ? ORDER BY created_at ASC",
            (_iso(),),
        )
        return [self._row_to_addend(r) for r in await cur.fetchall()]

    async def compose(self, base_prompt: str) -> str:
        """Glue the immutable base prompt with active addends.

        Order: base -> active addends (by created_at).
        """
        active = await self.active()
        parts = [base_prompt] + [a.text for a in active]
        return "\n\n".join(parts)

    async def persist_to_disk(self, path: str) -> None:
        """Write active addends to a SOUL.md-style file (YAML + markdown)."""
        active = await self.active()
        metadata = {
            "kind": "behavior-addends",
            "version": "0.2",
            "addends": [a.to_dict() for a in active],
        }
        body = "\n\n".join(f"## {a.id}\n\n{a.text}" for a in active)
        if not active:
            body = "No active addends."
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(write_frontmatter(metadata, body))

    # ------------------------------------------------------- VersionedState ABC

    async def get(self, key: str, version: Optional[int] = None) -> Optional[BehaviorAddend]:
        conn = await self._connect()
        cur = await conn.execute(
            "SELECT * FROM behavior_addends WHERE id = ?", (key,)
        )
        row = await cur.fetchone()
        return self._row_to_addend(row) if row else None

    async def put(
        self, key: str, value: str, *, actor: str = "agent", scope: str = "session"
    ) -> int:
        """Upsert a single addend under an explicit id (ABC-compatible)."""
        conn = await self._connect()
        created = datetime.now()
        expires = created + timedelta(seconds=3600)
        await conn.execute(
            "INSERT OR REPLACE INTO behavior_addends "
            "(id, text, ttl, created_at, scope, actor, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (key, value, 3600, _iso(created), scope, actor, _iso(expires)),
        )
        await conn.execute(
            "INSERT INTO behavior_journal (op, payload, timestamp, actor) VALUES ('put', ?, ?, ?)",
            (key, _iso(created), actor),
        )
        await conn.commit()
        self._mirror[key] = BehaviorAddend(
            id=key, text=value, ttl=3600, created_at=created,
            scope=scope, actor=actor, expires_at=expires,
        )
        cur = await conn.execute("SELECT seq FROM behavior_journal ORDER BY seq DESC LIMIT 1")
        row = await cur.fetchone()
        return int(row["seq"]) if row else 1

    async def rollback(self, version: int) -> bool:
        """Undo every mutation journaled after ``version`` (real rollback)."""
        conn = await self._connect()
        cur = await conn.execute(
            "SELECT * FROM behavior_journal WHERE seq > ? ORDER BY seq DESC", (version,)
        )
        rows = await cur.fetchall()
        undone = 0
        for row in rows:
            if row["op"] in ("add", "put"):
                await conn.execute("DELETE FROM behavior_addends WHERE id = ?", (row["payload"],))
                self._mirror.pop(row["payload"], None)
            elif row["op"] == "remove":
                data = _from_json(row["payload"])
                await conn.execute(
                    "INSERT OR REPLACE INTO behavior_addends "
                    "(id, text, ttl, created_at, scope, actor, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (data["id"], data["text"], data["ttl"], data["created_at"],
                     data["scope"], data["actor"], data["expires_at"]),
                )
                self._mirror[data["id"]] = BehaviorAddend(
                    id=data["id"], text=data["text"], ttl=int(data["ttl"]),
                    created_at=_parse_iso(data["created_at"]), scope=data["scope"],
                    actor=data["actor"], expires_at=_parse_iso(data["expires_at"]),
                )
            undone += 1
        await conn.execute("DELETE FROM behavior_journal WHERE seq > ?", (version,))
        await conn.commit()
        return undone > 0

    async def history(self, key: str) -> list[VersionEntry]:
        conn = await self._connect()
        cur = await conn.execute(
            "SELECT * FROM behavior_journal WHERE payload = ? ORDER BY seq ASC", (key,)
        )
        rows = await cur.fetchall()
        return [
            VersionEntry(
                version=r["seq"], key=key, value=r["op"],
                timestamp=_parse_iso(r["timestamp"]), actor=r["actor"], scope="session",
            )
            for r in rows
        ]

    # ------------------------------------------------------------------ helpers

    def mirror_active(self) -> list[BehaviorAddend]:
        """Sync mirror of non-expired addends (for snapshots)."""
        now = datetime.now()
        return sorted(
            (a for a in self._mirror.values() if a.expires_at > now),
            key=lambda a: a.created_at,
        )

    def _row_to_addend(self, row) -> BehaviorAddend:
        return BehaviorAddend(
            id=row["id"], text=row["text"], ttl=row["ttl"],
            created_at=_parse_iso(row["created_at"]), scope=row["scope"],
            actor=row["actor"], expires_at=_parse_iso(row["expires_at"]),
        )
