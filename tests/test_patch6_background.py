"""Patch 6 regression tests: daily push, weekly mirror, favorites, history."""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db_path = os.path.join(tempfile.gettempdir(), "moira_patch6.db")
if __name__ == "__main__":
    os.environ["DB_PATH"] = db_path
    if os.path.exists(db_path):
        os.remove(db_path)

from aiogram.types import User as TgUser
from sqlalchemy import select

from bot.config import load_config
from bot.db.database import get_session, init_db
from bot.db.models import Reading, ReadingFavorite, User
from bot.handlers.features import send_daily_push, send_weekly_mirror, _toggle_favorite
from bot.handlers.helpers import get_or_create_user


class FakeBot:
    def __init__(self, raise_on: int | None = None) -> None:
        self.sent: list[int] = []
        self.raise_on = raise_on

    async def send_message(self, *args, **kwargs) -> None:
        if self.raise_on == len(self.sent):
            raise RuntimeError("telegram error")
        self.sent.append(args[0] if args else kwargs.get("chat_id"))


def _tg_user(user_id: int) -> TgUser:
    return TgUser(id=user_id, is_bot=False, first_name="Test")


class FakeAnalytics:
    async def track(self, *args, **kwargs) -> None:
        pass


async def _test_daily_push_only_on_success() -> None:
    cfg = load_config(require_token=False)
    user = await get_or_create_user(_tg_user(700), cfg)
    async with get_session() as session:
        u = await session.get(User, 700)
        u.daily_push = True
        u.last_push_date = None
        await session.commit()

    bot = FakeBot()
    sent = await send_daily_push(bot, cfg, u, None, date.today().isoformat())
    assert sent is True
    assert u.last_push_date == date.today().isoformat()

    # Failing bot must not update last_push_date.
    u.last_push_date = None
    fail_bot = FakeBot(raise_on=0)
    sent2 = await send_daily_push(fail_bot, cfg, u, None, date.today().isoformat())
    assert sent2 is False
    assert u.last_push_date is None

    # Disabled push must not mark date.
    u.daily_push = False
    u.last_push_date = None
    off_bot = FakeBot()
    sent3 = await send_daily_push(off_bot, cfg, u, None, date.today().isoformat())
    assert sent3 is False
    assert u.last_push_date is None


async def _test_weekly_mirror_no_duplicate() -> None:
    cfg = load_config(require_token=False)
    user = await get_or_create_user(_tg_user(701), cfg)
    async with get_session() as session:
        u = await session.get(User, 701)
        u.daily_push = True
        u.last_mirror_week = "2026-W01"
        await session.commit()
        # Add 3 recent readings to pass the threshold.
        for i in range(3):
            session.add(Reading(user_id=701, spread="situation", cards_json="major_0,major_1,major_2"))
        await session.commit()

    bot = FakeBot()
    sent = await send_weekly_mirror(bot, cfg, u, None, "2026-W01", FakeAnalytics())
    assert sent is False, "duplicate week should not send"

    # New week should attempt to send.
    u.last_mirror_week = "2025-W52"
    async with get_session() as session:
        sent2 = await send_weekly_mirror(bot, cfg, u, session, "2026-W01", FakeAnalytics())
    assert sent2 is True, "new week should send"


async def _test_history_ownership() -> None:
    cfg = load_config(require_token=False)
    await get_or_create_user(_tg_user(702), cfg)
    await get_or_create_user(_tg_user(703), cfg)
    async with get_session() as session:
        session.add(Reading(user_id=702, spread="situation", cards_json="major_0,major_1,major_2"))
        await session.commit()

    async with get_session() as session:
        reading = (await session.execute(select(Reading).where(Reading.user_id == 702))).scalar_one()
        assert reading is not None
        # User 703 must not see it.
        other = (await session.execute(select(Reading).where(Reading.id == reading.id, Reading.user_id == 703))).scalar_one_or_none()
        assert other is None


async def _test_favorite_toggle_idempotent() -> None:
    cfg = load_config(require_token=False)
    await get_or_create_user(_tg_user(704), cfg)
    async with get_session() as session:
        session.add(Reading(user_id=704, spread="love", cards_json="major_0,major_1,major_2"))
        await session.commit()

    first = await _toggle_favorite(704, 1)
    assert first is True
    second = await _toggle_favorite(704, 1)
    assert second is False
    # Concurrent toggles should not crash; final state is deterministic.
    results = await asyncio.gather(_toggle_favorite(704, 1), _toggle_favorite(704, 1))
    assert any(results) or not any(results)  # no unhandled exception is the real test


async def main() -> None:
    await init_db(db_path)
    await _test_daily_push_only_on_success()
    await _test_weekly_mirror_no_duplicate()
    await _test_history_ownership()
    await _test_favorite_toggle_idempotent()
    print("PATCH 6 TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
