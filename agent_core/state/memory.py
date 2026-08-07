"""MemoryStore: versioned key-value memory with two layers.

Short-term — TTL-based, auto-expiry (SQLite rows with ``expires_at``).
Long-term  — cross-session (``scope="global"``), persistent, with
confidence scores and trust tiers (DeerFlow 2.0 pattern).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from ..format.trust import TrustTier
from .base import SQLiteVersionedState, VersionEntry, _from_json, _iso, _parse_iso, _to_json


@dataclass
class MemoryEntry:
    key: str
    value: Any
    version: int
    timestamp: datetime
    trust: TrustTier
    confidence: float  # 0.0–1.0
    ttl: Optional[int]
    actor: str
    scope: str  # "session" or "global"
    is_stale: bool


class MemoryStore(SQLiteVersionedState):
    """Key-value memory over VersionedState with TTL, trust and confidence."""

    def __init__(self, db_path: str = ":memory:"):
        super().__init__(db_path)
        self._keys: set[str] = set()  # synchronous mirror for snapshots

    async def _connect(self) -> Any:
        conn = await super()._connect()
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_entries (
                key TEXT NOT NULL,
                version INTEGER PRIMARY KEY AUTOINCREMENT,
                value TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                trust TEXT NOT NULL,
                confidence REAL NOT NULL,
                ttl INTEGER,
                expires_at TEXT,
                actor TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'session'
            )
            """
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_key ON memory_entries(key)"
        )
        await conn.commit()
        cur = await conn.execute("SELECT DISTINCT key FROM memory_entries")
        self._keys = {r["key"] for r in await cur.fetchall()}
        return conn

    # ------------------------------------------------------------------ core API

    async def get(
        self, key: str, version: Optional[int] = None
    ) -> Optional[MemoryEntry]:
        conn = await self._connect()
        if version is None:
            cur = await conn.execute(
                "SELECT * FROM memory_entries WHERE key = ? ORDER BY version DESC LIMIT 1",
                (key,),
            )
        else:
            cur = await conn.execute(
                "SELECT * FROM memory_entries WHERE key = ? AND version = ?",
                (key, version),
            )
        row = await cur.fetchone()
        return self._row_to_entry(row) if row else None

    async def put(
        self,
        key: str,
        value: Any,
        *,
        ttl: Optional[int] = None,
        trust: TrustTier = TrustTier.UNVERIFIED,
        confidence: float = 0.0,  # 0.0–1.0
        actor: str = "agent",
        scope: str = "session",
    ) -> int:
        conn = await self._connect()
        expires_at: Optional[str] = None
        if ttl is not None:
            expires_at = _iso(datetime.now() + timedelta(seconds=ttl))
        cur = await conn.execute(
            "INSERT INTO memory_entries "
            "(key, value, timestamp, trust, confidence, ttl, expires_at, actor, scope) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (key, _to_json(value), _iso(), trust.value, confidence, ttl, expires_at, actor, scope),
        )
        await conn.commit()
        self._keys.add(key)
        return int(cur.lastrowid)

    async def search(self, pattern: str) -> list[MemoryEntry]:
        """Return the latest version of every key matching ``pattern``."""
        conn = await self._connect()
        cur = await conn.execute(
            """
            SELECT m.* FROM memory_entries m
            JOIN (SELECT key, MAX(version) AS v FROM memory_entries GROUP BY key) latest
              ON m.key = latest.key AND m.version = latest.v
            WHERE m.key LIKE ?
            ORDER BY m.version DESC
            """,
            (f"%{pattern}%",),
        )
        return [self._row_to_entry(r) for r in await cur.fetchall()]

    async def stale_keys(self) -> list[str]:
        """Keys whose latest version has expired TTL."""
        conn = await self._connect()
        cur = await conn.execute(
            """
            SELECT m.key FROM memory_entries m
            JOIN (SELECT key, MAX(version) AS v FROM memory_entries GROUP BY key) latest
              ON m.key = latest.key AND m.version = latest.v
            WHERE m.expires_at IS NOT NULL AND m.expires_at < ?
            """,
            (_iso(),),
        )
        return [r["key"] for r in await cur.fetchall()]

    async def promote_to_long_term(self, key: str) -> bool:
        """Move an entry from short-term to long-term (global scope, no TTL)."""
        entry = await self.get(key)
        if entry is None or entry.scope == "global":
            return False
        await self.put(
            key,
            entry.value,
            ttl=None,
            trust=entry.trust,
            confidence=entry.confidence,
            actor=entry.actor,
            scope="global",
        )
        return True

    async def by_confidence(self, threshold: float = 0.7) -> list[MemoryEntry]:
        conn = await self._connect()
        cur = await conn.execute(
            """
            SELECT m.* FROM memory_entries m
            JOIN (SELECT key, MAX(version) AS v FROM memory_entries GROUP BY key) latest
              ON m.key = latest.key AND m.version = latest.v
            WHERE m.confidence >= ?
            ORDER BY m.confidence DESC
            """,
            (threshold,),
        )
        return [self._row_to_entry(r) for r in await cur.fetchall()]

    async def delete(self, key: str) -> bool:
        conn = await self._connect()
        cur = await conn.execute("DELETE FROM memory_entries WHERE key = ?", (key,))
        await conn.commit()
        if cur.rowcount > 0:
            self._keys.discard(key)
            return True
        return False

    # ------------------------------------------------------- VersionedState ABC

    async def rollback(self, version: int) -> bool:
        """Delete every memory version newer than ``version``."""
        conn = await self._connect()
        cur = await conn.execute("DELETE FROM memory_entries WHERE version > ?", (version,))
        await conn.commit()
        cur2 = await conn.execute("SELECT DISTINCT key FROM memory_entries")
        self._keys = {r["key"] for r in await cur2.fetchall()}
        return cur.rowcount > 0

    async def history(self, key: str) -> list[VersionEntry]:
        conn = await self._connect()
        cur = await conn.execute(
            "SELECT * FROM memory_entries WHERE key = ? ORDER BY version ASC", (key,)
        )
        rows = await cur.fetchall()
        return [
            VersionEntry(
                version=r["version"],
                key=r["key"],
                value=_from_json(r["value"]),
                timestamp=_parse_iso(r["timestamp"]),
                actor=r["actor"],
                scope=r["scope"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------ helpers

    def mirror_keys(self) -> set[str]:
        """Synchronous key mirror (for HarnessState.snapshot)."""
        return set(self._keys)

    def _row_to_entry(self, row) -> MemoryEntry:
        is_stale = False
        if row["expires_at"] is not None:
            is_stale = _parse_iso(row["expires_at"]) < datetime.now()
        return MemoryEntry(
            key=row["key"],
            value=_from_json(row["value"]),
            version=row["version"],
            timestamp=_parse_iso(row["timestamp"]),
            trust=TrustTier(row["trust"]),
            confidence=float(row["confidence"]),
            ttl=row["ttl"],
            actor=row["actor"],
            scope=row["scope"],
            is_stale=is_stale,
        )
