"""SubagentRegistry: sub-agent definitions + nuclear-family messaging.

Messaging is scoped to the nuclear family (parent/sibling/child) — a
message can only be sent to a subagent registered in the same registry.
Cross-session messaging is NOT supported (no global chatter).
Retained sub-agents drop after ``idle_timeout`` (Prime Agent).
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from .base import SQLiteVersionedState, VersionEntry, _from_json, _iso, _parse_iso, _to_json


@dataclass
class SubagentDefinition:
    name: str
    goal: str
    system_prompt: str
    tools: list[str]  # allowed tool names
    max_iterations: int
    idle_timeout: int = 1800  # 30 min (Prime Agent: drop after idle)


class SubagentRegistry(SQLiteVersionedState):
    """Registry of sub-agent definitions with journaled rollback."""

    def __init__(self, db_path: str = ":memory:"):
        super().__init__(db_path)
        self._mirror: dict[str, tuple[SubagentDefinition, datetime]] = {}

    async def _connect(self) -> Any:
        conn = await super()._connect()
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subagents (
                name TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                tools TEXT NOT NULL,
                max_iterations INTEGER NOT NULL,
                idle_timeout INTEGER NOT NULL,
                scope TEXT NOT NULL DEFAULT 'session',
                last_active TEXT NOT NULL,
                reg_version INTEGER NOT NULL
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subagents_history (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                op TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL
            )
            """
        )
        await conn.commit()
        cur = await conn.execute("SELECT * FROM subagents")
        self._mirror = {}
        for r in await cur.fetchall():
            self._mirror[r["name"]] = (
                self._row_to_definition(r),
                _parse_iso(r["last_active"]),
            )
        return conn

    # ------------------------------------------------------------------ core API

    async def register(
        self, definition: SubagentDefinition, *, scope: str = "session", actor: str = "agent"
    ) -> str:
        conn = await self._connect()
        now = datetime.now()
        cur = await conn.execute(
            "INSERT INTO subagents_history (name, op, payload, timestamp, actor) "
            "VALUES (?, 'register', ?, ?, ?)",
            (definition.name, _to_json(asdict(definition)), _iso(now), actor),
        )
        seq = int(cur.lastrowid)
        await conn.execute(
            "INSERT OR REPLACE INTO subagents "
            "(name, goal, system_prompt, tools, max_iterations, idle_timeout, scope, last_active, reg_version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (definition.name, definition.goal, definition.system_prompt,
             _to_json(definition.tools), definition.max_iterations,
             definition.idle_timeout, scope, _iso(now), seq),
        )
        await conn.commit()
        self._mirror[definition.name] = (definition, now)
        return definition.name

    async def get(self, name: str, version: Optional[int] = None) -> Optional[SubagentDefinition]:
        conn = await self._connect()
        cur = await conn.execute("SELECT * FROM subagents WHERE name = ?", (name,))
        row = await cur.fetchone()
        return self._row_to_definition(row) if row else None

    async def list(self) -> list[str]:
        conn = await self._connect()
        cur = await conn.execute("SELECT name FROM subagents ORDER BY name")
        return [r["name"] for r in await cur.fetchall()]

    async def delete(self, name: str) -> bool:
        """Delete a subagent definition (retained sub-agents also drop on idle)."""
        conn = await self._connect()
        cur = await conn.execute("SELECT * FROM subagents WHERE name = ?", (name,))
        row = await cur.fetchone()
        if row is None:
            return False
        await conn.execute("DELETE FROM subagents WHERE name = ?", (name,))
        await conn.execute(
            "INSERT INTO subagents_history (name, op, payload, timestamp, actor) "
            "VALUES (?, 'delete', ?, ?, 'agent')",
            (name, _to_json(dict(row)), _iso()),
        )
        await conn.commit()
        self._mirror.pop(name, None)
        return True

    async def message(self, name: str, message: str) -> str:
        """Send a message to a subagent (nuclear-family scoped).

        Returns a mock acknowledgement (echo + ack) — the framework is
        LLM-agnostic, so a real subagent would be wired up by the host
        application. Cross-session chatter is not supported.
        """
        conn = await self._connect()
        cur = await conn.execute("SELECT * FROM subagents WHERE name = ?", (name,))
        row = await cur.fetchone()
        if row is None:
            return (
                f"error: unknown subagent '{name}' — messaging is scoped "
                f"to the nuclear family (parent/sibling/child)"
            )
        definition = self._row_to_definition(row)
        last_active = _parse_iso(row["last_active"])
        now = datetime.now()
        if now - last_active > timedelta(seconds=definition.idle_timeout):
            await self.delete(name)
            return f"error: subagent '{name}' dropped after idle timeout"
        await conn.execute(
            "UPDATE subagents SET last_active = ? WHERE name = ?", (_iso(now), name)
        )
        await conn.commit()
        self._mirror[name] = (definition, now)
        return f"[{name}] ack: {message}"

    async def list_active(self) -> list[str]:
        """Names of subagents that have not exceeded their idle timeout."""
        conn = await self._connect()
        cur = await conn.execute("SELECT * FROM subagents")
        active = []
        for r in await cur.fetchall():
            definition = self._row_to_definition(r)
            if datetime.now() - _parse_iso(r["last_active"]) <= timedelta(
                seconds=definition.idle_timeout
            ):
                active.append(r["name"])
        return sorted(active)

    # ------------------------------------------------------- VersionedState ABC

    async def put(
        self, name: str, value: Any, *, actor: str = "agent", scope: str = "session"
    ) -> int:
        if isinstance(value, SubagentDefinition):
            definition = value
            if not definition.name:
                definition.name = name
        else:
            definition = SubagentDefinition(
                name=name, goal=str(value), system_prompt="",
                tools=[], max_iterations=3, idle_timeout=1800,
            )
        await self.register(definition, scope=scope, actor=actor)
        conn = await self._connect()
        cur = await conn.execute(
            "SELECT seq FROM subagents_history ORDER BY seq DESC LIMIT 1"
        )
        row = await cur.fetchone()
        return int(row["seq"]) if row else 1

    async def rollback(self, version: int) -> bool:
        """Undo every register/delete journaled after ``version``."""
        conn = await self._connect()
        cur = await conn.execute(
            "SELECT * FROM subagents_history WHERE seq > ? ORDER BY seq DESC", (version,)
        )
        rows = await cur.fetchall()
        undone = 0
        for row in rows:
            payload = _from_json(row["payload"])
            if row["op"] == "register":
                await conn.execute(
                    "DELETE FROM subagents WHERE reg_version = ?", (row["seq"],)
                )
                self._mirror.pop(payload["name"], None)
            elif row["op"] == "delete":
                data = _from_json(row["payload"])
                await conn.execute(
                    "INSERT OR REPLACE INTO subagents "
                    "(name, goal, system_prompt, tools, max_iterations, idle_timeout, scope, last_active, reg_version) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (data["name"], data["goal"], data["system_prompt"], data["tools"],
                     data["max_iterations"], data["idle_timeout"], data["scope"],
                     data["last_active"], row["seq"]),
                )
                definition = SubagentDefinition(
                    name=data["name"], goal=data["goal"], system_prompt=data["system_prompt"],
                    tools=data["tools"], max_iterations=data["max_iterations"],
                    idle_timeout=data["idle_timeout"],
                )
                self._mirror[data["name"]] = (definition, _parse_iso(data["last_active"]))
            undone += 1
        await conn.execute("DELETE FROM subagents_history WHERE seq > ?", (version,))
        await conn.commit()
        return undone > 0

    async def history(self, key: str) -> list[VersionEntry]:
        conn = await self._connect()
        cur = await conn.execute(
            "SELECT * FROM subagents_history WHERE name = ? ORDER BY seq ASC", (key,)
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

    def mirror_definitions(self) -> dict[str, SubagentDefinition]:
        """Sync mirror name -> definition (for HarnessState.snapshot)."""
        return {name: defn for name, (defn, _) in self._mirror.items()}

    def _row_to_definition(self, row) -> SubagentDefinition:
        return SubagentDefinition(
            name=row["name"],
            goal=row["goal"],
            system_prompt=row["system_prompt"],
            tools=_from_json(row["tools"]),
            max_iterations=row["max_iterations"],
            idle_timeout=row["idle_timeout"],
        )
