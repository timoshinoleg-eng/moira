"""Regression: /delete_my_data must also remove feedback and push-delivery rows."""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone

from aiogram.types import User as TgUser
from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import load_config
from bot.db.database import close_db, get_session, init_db
from bot.db.models import PushDelivery, Reading, ReadingFeedback, User


class FakeMessage:
    def __init__(self, user_id: int) -> None:
        self.from_user = TgUser(id=user_id, is_bot=False, first_name="Test")
        self.sent: list[str] = []

    async def answer(self, text: str, **kwargs) -> None:
        self.sent.append(text)


class FakeAnalytics:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    async def track(self, user_id: int, event: str, **props) -> None:
        self.events.append((user_id, event, props))


def test_delete_my_data_removes_feedback_and_push_delivery(tmp_path) -> None:
    from bot.handlers.start import cmd_delete_my_data

    async def run() -> None:
        cfg = load_config(require_token=False)
        await init_db(str(tmp_path / "moira-delete-all.db"))
        async with get_session() as session:
            session.add(User(id=31, language="ru"))
            session.add(Reading(id=9, user_id=31, spread="love", cards_json="major_0"))
            session.add(
                ReadingFeedback(user_id=31, reading_id=9, value="positive", checkpoint="immediate")
            )
            session.add(
                PushDelivery(
                    user_id=31,
                    kind="daily_altar",
                    local_period="2026-09-27",
                    scheduled_at=datetime(2026, 9, 27, 6, 0, tzinfo=timezone.utc),
                    status="planned",
                )
            )
            await session.commit()

        await cmd_delete_my_data(FakeMessage(31), cfg, FakeAnalytics())

        async with get_session() as session:
            assert (await session.execute(select(ReadingFeedback))).scalars().all() == []
            assert (await session.execute(select(PushDelivery))).scalars().all() == []
            assert (await session.execute(select(Reading))).scalars().all() == []
            assert (await session.execute(select(User).where(User.id == 31))).scalars().all() == []
        await close_db()

    asyncio.run(run())
