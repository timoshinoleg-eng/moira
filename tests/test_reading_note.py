"""QW-4: private reading notes — ownership, truncation, cascade, privacy."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys

import pytest
from aiogram.types import User as TgUser
from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import load_config
from bot.db.database import close_db, get_session, init_db
from bot.db.models import Event, Reading, ReadingNote, User
from bot.services.analytics import Analytics
from bot.services.reading_notes import (
    MAX_NOTE_LENGTH,
    NoteOwnershipError,
    delete_reading_note,
    get_reading_note,
    save_reading_note,
)


class FakeMessage:
    def __init__(self, user_id: int, text: str | None = None) -> None:
        self.from_user = TgUser(id=user_id, is_bot=False, first_name="Test")
        self.text = text
        self.sent: list[str] = []

    async def answer(self, text: str, **kwargs) -> None:
        self.sent.append(text)


class FakeState:
    """Minimal FSMContext stand-in recording clear() calls."""

    def __init__(self, data: dict | None = None) -> None:
        self._data = dict(data or {})
        self.cleared = False

    async def get_data(self) -> dict:
        return dict(self._data)

    async def clear(self) -> None:
        self._data = {}
        self.cleared = True


class FakeAnalytics:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    async def track(self, user_id: int, event: str, **props) -> None:
        self.events.append((user_id, event, props))


async def _seed(db_path: str, user_id: int = 21, reading_id: int = 5) -> None:
    await init_db(db_path)
    async with get_session() as session:
        session.add(User(id=user_id, language="ru"))
        session.add(Reading(id=reading_id, user_id=user_id, spread="love", cards_json="major_0"))
        await session.commit()


def test_foreign_reading_refused_without_write(tmp_path) -> None:
    async def run() -> None:
        await _seed(str(tmp_path / "moira-note-own.db"))
        async with get_session() as session:
            with pytest.raises(NoteOwnershipError):
                await save_reading_note(session, user_id=99, reading_id=5, text="intruder note")
            with pytest.raises(NoteOwnershipError):
                await get_reading_note(session, user_id=99, reading_id=5)
            with pytest.raises(NoteOwnershipError):
                await delete_reading_note(session, user_id=99, reading_id=5)
            assert (await session.execute(select(ReadingNote))).scalars().all() == []
        await close_db()

    asyncio.run(run())


def test_upsert_and_hard_truncation(tmp_path) -> None:
    assert MAX_NOTE_LENGTH == 1000

    async def run() -> None:
        await _seed(str(tmp_path / "moira-note-upsert.db"))
        async with get_session() as session:
            await save_reading_note(session, user_id=21, reading_id=5, text="first version")
            await session.commit()
            note = await save_reading_note(session, user_id=21, reading_id=5, text="x" * 1500)
            await session.commit()
            assert len(note.text) == MAX_NOTE_LENGTH
            rows = (await session.execute(select(ReadingNote))).scalars().all()
            assert len(rows) == 1
            assert await get_reading_note(session, user_id=21, reading_id=5) is not None
            assert await delete_reading_note(session, user_id=21, reading_id=5) is True
            assert await delete_reading_note(session, user_id=21, reading_id=5) is False
            await session.commit()
            with pytest.raises(ValueError):
                await save_reading_note(session, user_id=21, reading_id=5, text="   ")
        await close_db()

    asyncio.run(run())


def test_delete_my_data_removes_notes(tmp_path) -> None:
    from bot.handlers.start import cmd_delete_my_data

    async def run() -> None:
        cfg = load_config(require_token=False)
        await _seed(str(tmp_path / "moira-note-cascade.db"), user_id=22, reading_id=6)
        async with get_session() as session:
            await save_reading_note(session, user_id=22, reading_id=6, text="private note")
            await session.commit()
        await cmd_delete_my_data(FakeMessage(22), cfg, FakeAnalytics())
        async with get_session() as session:
            assert (await session.execute(select(ReadingNote))).scalars().all() == []
            assert (await session.execute(select(Reading))).scalars().all() == []
        await close_db()

    asyncio.run(run())


def test_note_text_never_reaches_analytics(tmp_path) -> None:
    async def run() -> None:
        marker = "NOTE_SECRET_MARKER_9f8e7d6c"
        await init_db(str(tmp_path / "moira-note-analytics.db"))
        cfg = load_config(require_token=False)
        analytics = Analytics(cfg)
        await analytics.track(23, "note_created", reading_id=7)
        # Even a mistaken text kwarg is stripped by the allowlist.
        assert analytics._safe_props({"reading_id": 7, "text": marker}) == {"reading_id": 7}
        async with get_session() as session:
            rows = (await session.execute(select(Event))).scalars().all()
            assert rows, "event mirror must persist"
            for row in rows:
                assert marker not in row.props_json
                assert json.loads(row.props_json).get("reading_id") == 7
        await close_db()

    asyncio.run(run())


def test_notes_migration_downgrade_cycle(tmp_path) -> None:
    import sqlite3

    db_path = str(tmp_path / "moira-note-cycle.db")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["DB_PATH"] = db_path

    def alembic(*args: str):
        return subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=root, env=env, capture_output=True, text=True,
        )

    assert alembic("upgrade", "head").returncode == 0
    assert alembic("downgrade", "-1").returncode == 0
    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "reading_notes" not in tables
    assert alembic("upgrade", "head").returncode == 0
    assert alembic("check").returncode == 0


def test_cancel_token_never_stores_note(tmp_path) -> None:
    from bot.handlers.reading import process_note
    from bot.i18n import t

    async def run() -> None:
        await _seed(str(tmp_path / "moira-note-cancel.db"))
        async with get_session() as session:
            await save_reading_note(session, user_id=21, reading_id=5, text="precious")
            await session.commit()
        cfg = load_config(require_token=False)
        analytics = FakeAnalytics()
        state = FakeState({"reading_id": 5})
        msg = FakeMessage(21, text="меню")
        await process_note(msg, state, cfg, analytics)
        assert state.cleared
        async with get_session() as session:
            note = await get_reading_note(session, user_id=21, reading_id=5)
            assert note is not None and note.text == "precious", "cancel token overwrote the note"
        assert t("ru", "menu_help") in msg.sent
        assert analytics.events == [], "cancel must not track note_created"
        await close_db()

    asyncio.run(run())


def test_cmd_start_clears_pending_note_state(tmp_path) -> None:
    from bot.handlers.start import cmd_start

    async def run() -> None:
        await _seed(str(tmp_path / "moira-note-start.db"))
        cfg = load_config(require_token=False)
        state = FakeState({"reading_id": 5})
        await cmd_start(FakeMessage(21), state, cfg, FakeAnalytics())
        assert state.cleared and state._data == {}, "/start must drop the note prompt"
        await close_db()

    asyncio.run(run())


def test_note_save_failure_is_answered(tmp_path, monkeypatch) -> None:
    import bot.handlers.reading as reading_module
    from bot.handlers.reading import process_note
    from bot.i18n import t

    async def boom(session, **kwargs) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(reading_module, "save_reading_note", boom)

    async def run() -> None:
        await _seed(str(tmp_path / "moira-note-fail.db"))
        cfg = load_config(require_token=False)
        msg = FakeMessage(21, text="an honest note")
        await process_note(msg, FakeState({"reading_id": 5}), cfg, FakeAnalytics())
        assert msg.sent == [t("ru", "note_save_failed")], "user left without an answer"
        await close_db()

    asyncio.run(run())
