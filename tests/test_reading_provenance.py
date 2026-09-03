"""QW-0 provenance: generation_id threading, result_json privacy, feedback upsert, migration downgrade."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeCompletions:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses: list[object]) -> None:
        from types import SimpleNamespace

        self.completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def _valid_completion(drawn) -> object:
    from types import SimpleNamespace

    from bot.llm.adapter import TarotReadingResult

    def pad(text: str, minimum: int, maximum: int) -> str:
        while len(text) < minimum:
            text = f"{text} {text}"
        return text[:maximum]

    payload = TarotReadingResult(
        headline="Точный и спокойный ответ",
        opening=pad("Карты открывают спокойную динамику и ясный фокус.", 80, 180),
        card_interpretations=[
            {
                "position": card.position_label["ru"],
                "card_name": card.card.name("ru"),
                "orientation": "reversed" if card.reversed else "upright",
                "core_message": pad("Эта карта показывает конкретное напряжение и полезный следующий шаг.", 120, 300),
                "symbolic_detail": "",
                "context_connection": "",
            }
            for card in drawn
        ],
        synthesis=pad("Синтез объединяет карты в одну практическую линию без обещаний и предсказаний.", 240, 500),
        practical_focus=pad("Выберите один небольшой проверяемый шаг и выполните его в ближайшее время.", 100, 220),
        reflection_question="Что поможет сделать этот небольшой шаг сегодня?",
        voice_summary=pad("Устная версия удерживает главную линию расклада и предлагает спокойно выбрать следующий шаг.", 180, 380),
        share_summary=pad("Карты предлагают увидеть главное напряжение, выбрать ясный фокус и двигаться небольшим шагом.", 100, 220),
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=payload.model_dump_json()))],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=22),
    )


def test_generation_id_threads_through_result_usage_and_reading(tmp_path, monkeypatch) -> None:
    from dataclasses import replace

    import openai

    from bot.config import load_config
    from bot.db.database import close_db, get_session, init_db
    from bot.db.models import LlmUsage, Reading
    from bot.llm import adapter
    from bot.tarot import draw

    async def run() -> None:
        cfg = replace(
            load_config(require_token=False),
            openrouter_api_key="test-key",
            db_path=str(tmp_path / "moira-provenance.db"),
        )
        await init_db(cfg.db_path)
        drawn = draw("love")
        marker = f"SECRET_QUESTION_{uuid.uuid4().hex}"
        client = FakeClient([_valid_completion(drawn)])
        monkeypatch.setattr(openai, "AsyncOpenAI", lambda **kwargs: client)

        result, generation_id = await adapter.interpret_reading(
            cfg, "ru", "Расклад «Любовь»", marker, drawn, user_id=7, spread_id="love"
        )
        assert result is not None
        assert len(generation_id) == 32 and int(generation_id, 16) >= 0
        assert result.generation_id == generation_id

        # Only the validated Pydantic payload is stored — never the question.
        result_json = result.model_dump(exclude={"generation_id"}, mode="json")
        assert marker not in json.dumps(result_json, ensure_ascii=False)

        async with get_session() as session:
            usage = (await session.execute(select(LlmUsage))).scalar_one()
            assert usage.generation_id == generation_id
            session.add(
                Reading(
                    user_id=7,
                    spread="love",
                    cards_json="major_0,major_1",
                    question=marker,
                    interpretation="plain",
                    response_mode="llm",
                    generation_id=generation_id,
                    result_json=result_json,
                    draw_engine_version="v1",
                    deck_version="v1",
                    spread_version="v1",
                )
            )
            await session.commit()
            # Acceptance join: prompt version + model -> positive rate per spread.
            row = (
                await session.execute(
                    select(Reading.id, LlmUsage.prompt_version, LlmUsage.model)
                    .join(LlmUsage, LlmUsage.generation_id == Reading.generation_id)
                    .where(Reading.spread == "love")
                )
            ).one()
            assert row[1] == adapter.PROMPT_VERSION
        await close_db()

    asyncio.run(run())


def test_interpret_reading_without_key_still_returns_generation_id(tmp_path) -> None:
    from dataclasses import replace

    from bot.config import load_config
    from bot.db.database import close_db, init_db
    from bot.llm import adapter
    from bot.tarot import draw

    async def run() -> None:
        cfg = replace(
            load_config(require_token=False),
            openrouter_api_key=None,
            db_path=str(tmp_path / "moira-provenance-nokey.db"),
        )
        await init_db(cfg.db_path)
        result, generation_id = await adapter.interpret_reading(
            cfg, "ru", "Расклад «Ситуация»", "q", draw("situation"), user_id=1, spread_id="situation"
        )
        assert result is None
        assert len(generation_id) == 32 and int(generation_id, 16) >= 0
        await close_db()

    asyncio.run(run())


def test_feedback_upsert_updates_instead_of_duplicating(tmp_path) -> None:
    from bot.db.database import close_db, get_session, init_db
    from bot.db.models import Reading, ReadingFeedback, User
    from bot.handlers.reading import upsert_reading_feedback

    async def run() -> None:
        await init_db(str(tmp_path / "moira-feedback.db"))
        async with get_session() as session:
            session.add(User(id=11, language="ru"))
            session.add(Reading(id=1, user_id=11, spread="love", cards_json="major_0", generation_id="gid-1"))
            await session.commit()
            await upsert_reading_feedback(
                session, user_id=11, reading_id=1, generation_id="gid-1",
                value="positive", checkpoint="immediate",
            )
            await session.commit()
            await upsert_reading_feedback(
                session, user_id=11, reading_id=1, generation_id="gid-1",
                value="negative", checkpoint="immediate",
            )
            await session.commit()
            rows = (await session.execute(select(ReadingFeedback))).scalars().all()
            assert len(rows) == 1
            assert rows[0].value == "negative"
            assert rows[0].generation_id == "gid-1"
            # A repeat direct insert violates the unique constraint.
            session.add(
                ReadingFeedback(user_id=11, reading_id=1, value="positive", checkpoint="immediate")
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
        await close_db()

    asyncio.run(run())


def test_migration_downgrade_and_upgrade_cycle(tmp_path) -> None:
    import sqlite3

    db_path = str(tmp_path / "moira-prov-cycle.db")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["DB_PATH"] = db_path

    def alembic(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=root, env=env, capture_output=True, text=True,
        )

    assert alembic("upgrade", "head").returncode == 0
    # Pinned revisions, not "-1": the cycle must survive newer migrations on top.
    assert alembic("downgrade", "0009_reading_provenance_feedback").returncode == 0
    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "reading_feedback" in tables
    assert alembic("downgrade", "0008_push_delivery_foundation").returncode == 0
    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "reading_feedback" not in tables
    assert alembic("upgrade", "head").returncode == 0
    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "reading_feedback" in tables
    check = alembic("check")
    assert check.returncode == 0, f"alembic check failed: {check.stderr}"
