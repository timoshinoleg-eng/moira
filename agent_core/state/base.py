"""VersionedState ABC + SQLite-backed implementation.

Storage: SQLite through ``aiosqlite``. Table ``state_history``:
``version (INTEGER PK AUTOINCREMENT), key (TEXT), value (TEXT/JSON),
timestamp (TEXT ISO), actor (TEXT), scope (TEXT DEFAULT 'session')``.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import aiosqlite

from ..format.frontmatter import json_safe


@dataclass
class VersionEntry:
    version: int
    key: str
    value: Any
    timestamp: datetime
    actor: str  # "agent:...", "human:...", "process:..."
    scope: str  # "session" or "global"


_OPEN_STORES: set = set()


async def close_all_connections() -> None:
    """Close every open SQLite connection created by this library.

    Also resets each store's ``_conn`` to None so that store objects
    remain picklable (e.g. for kernel checkpoints).
    """
    for state in list(_OPEN_STORES):
        try:
            await state.close()
        except Exception:
            pass
    _OPEN_STORES.clear()


def _iso(ts: Optional[datetime] = None) -> str:
    return (ts or datetime.now()).isoformat(timespec="microseconds")


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _to_json(value: Any) -> str:
    return json.dumps(json_safe(value), ensure_ascii=False)


def _from_json(raw: str) -> Any:
    return json.loads(raw)


class VersionedState(ABC):
    """Abstract base class for every mutable state component.

    Every mutation creates a new version; ``rollback`` reverts the
    store to an earlier version; ``history`` lists all versions of a key.
    """

    @abstractmethod
    async def get(self, key: str, version: Optional[int] = None) -> Any:
        """Read a value; ``version=None`` returns the latest version."""

    @abstractmethod
    async def put(
        self, key: str, value: Any, *, actor: str = "agent", scope: str = "session"
    ) -> int:
        """Store a value and return the new version number.

        ``scope``: "session" — session-local (default);
        "global" — persists across sessions.
        """

    @abstractmethod
    async def rollback(self, version: int) -> bool:
        """Roll the state back to the given version."""

    @abstractmethod
    async def history(self, key: str) -> list[VersionEntry]:
        """Return the version history of a key (oldest first)."""


class SQLiteVersionedState(VersionedState):
    """Concrete key-value versioned state on SQLite (aiosqlite)."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def _connect(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
            _OPEN_STORES.add(self)
            await self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS state_history (
                    version INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'session'
                )
                """
            )
            await self._conn.commit()
        return self._conn

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
        _OPEN_STORES.discard(self)

    async def get(self, key: str, version: Optional[int] = None) -> Optional[VersionEntry]:
        conn = await self._connect()
        if version is None:
            cur = await conn.execute(
                "SELECT * FROM state_history WHERE key = ? ORDER BY version DESC LIMIT 1",
                (key,),
            )
        else:
            cur = await conn.execute(
                "SELECT * FROM state_history WHERE key = ? AND version = ?",
                (key, version),
            )
        row = await cur.fetchone()
        return self._row_to_entry(row) if row else None

    async def put(
        self, key: str, value: Any, *, actor: str = "agent", scope: str = "session"
    ) -> int:
        conn = await self._connect()
        cur = await conn.execute(
            "INSERT INTO state_history (key, value, timestamp, actor, scope) "
            "VALUES (?, ?, ?, ?, ?)",
            (key, _to_json(value), _iso(), actor, scope),
        )
        await conn.commit()
        return int(cur.lastrowid)

    async def rollback(self, version: int) -> bool:
        """Delete every row newer than ``version`` (state-level rollback)."""
        conn = await self._connect()
        cur = await conn.execute("DELETE FROM state_history WHERE version > ?", (version,))
        await conn.commit()
        return cur.rowcount > 0

    async def history(self, key: str) -> list[VersionEntry]:
        conn = await self._connect()
        cur = await conn.execute(
            "SELECT * FROM state_history WHERE key = ? ORDER BY version ASC", (key,)
        )
        rows = await cur.fetchall()
        return [self._row_to_entry(r) for r in rows]

    def _row_to_entry(self, row) -> VersionEntry:
        return VersionEntry(
            version=row["version"],
            key=row["key"],
            value=_from_json(row["value"]),
            timestamp=_parse_iso(row["timestamp"]),
            actor=row["actor"],
            scope=row["scope"],
        )
