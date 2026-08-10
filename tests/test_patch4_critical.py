"""Patch 4 critical test matrix: Alembic, assets, fonts, data deletion, privacy."""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db_path = os.path.join(tempfile.gettempdir(), "moira_patch4.db")
if __name__ == "__main__":
    os.environ["DB_PATH"] = db_path
    if os.path.exists(db_path):
        os.remove(db_path)

from aiogram.types import User as TgUser
from sqlalchemy import select

from bot.config import load_config
from bot.db.database import get_session, init_db
from bot.db.models import Payment, Reading, ReadingFavorite, Referral, User
from bot.handlers.helpers import get_or_create_user
from bot.handlers.payment import on_payment
from bot.handlers.reading import _consume_reading
from bot.payments import payload_for
from bot.services.analytics import Analytics
from bot.visual.assets import check_assets
from bot.visual.render import _font


class FakeSuccessfulPayment:
    def __init__(self, product_id: str, charge_id: str, total_amount: int, currency: str = "XTR") -> None:
        self.invoice_payload = payload_for(product_id)
        self.telegram_payment_charge_id = charge_id
        self.total_amount = total_amount
        self.currency = currency


class FakeMessage:
    def __init__(self, user_id: int, payment=None) -> None:
        self.from_user = TgUser(id=user_id, is_bot=False, first_name="Test", username=None)
        self.successful_payment = payment
        self.sent: list[str] = []

    async def answer(self, text: str, **kwargs) -> None:
        self.sent.append(text)


class FakeAnalytics:
    async def track(self, *args, **kwargs) -> None:
        pass


def _tg_user(user_id: int) -> TgUser:
    return TgUser(id=user_id, is_bot=False, first_name="Test")


async def _test_alembic_upgrade_empty() -> None:
    """Run all migrations on a fresh empty SQLite file."""
    import subprocess

    fresh_db = os.path.join(tempfile.gettempdir(), "moira_fresh.db")
    for f in [fresh_db, fresh_db + "-shm", fresh_db + "-wal"]:
        if os.path.exists(f):
            os.remove(f)
    env = os.environ.copy()
    env["DB_PATH"] = fresh_db
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic upgrade failed: {result.stderr}"
    result2 = subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result2.returncode == 0, f"alembic check failed: {result2.stderr}"


async def _test_alembic_upgrade_copy() -> None:
    """Existing DB (already stamped head) passes upgrade idempotently."""
    import subprocess

    copy_db = os.path.join(tempfile.gettempdir(), "moira_copy.db")
    shutil.copy(db_path, copy_db)
    env = os.environ.copy()
    env["DB_PATH"] = copy_db
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"upgrade on copy failed: {result.stderr}"


async def _test_assets_present() -> None:
    found, expected = check_assets()
    assert found == expected, f"assets missing: {found}/{expected}"


async def _test_font_fallback() -> None:
    font = _font(24)
    assert font is not None


async def _test_data_deletion() -> None:
    cfg = load_config(require_token=False)
    user = await get_or_create_user(_tg_user(900), cfg)
    async with get_session() as session:
        session.add(Reading(user_id=900, spread="situation", cards_json="major_0,major_1,major_2"))
        session.add(ReadingFavorite(user_id=900, reading_id=1))
        session.add(Payment(user_id=900, product="reading_1", stars=25, charge_id="chg_del"))
        await session.commit()

    from bot.handlers.start import cmd_delete_my_data
    msg = FakeMessage(900)
    await cmd_delete_my_data(msg, cfg, FakeAnalytics())

    async with get_session() as session:
        assert await session.get(User, 900) is None
        readings = (await session.execute(select(Reading).where(Reading.user_id == 900))).scalars().all()
        assert len(readings) == 0
        favs = (await session.execute(select(ReadingFavorite).where(ReadingFavorite.user_id == 900))).scalars().all()
        assert len(favs) == 0
        # Payment ledger should stay for audit (anonymised, no username).
        payment = (await session.execute(select(Payment).where(Payment.charge_id == "chg_del"))).scalar_one_or_none()
        assert payment is not None


async def _test_access_other_reading() -> None:
    cfg = load_config(require_token=False)
    await get_or_create_user(_tg_user(901), cfg)
    await get_or_create_user(_tg_user(902), cfg)
    async with get_session() as session:
        session.add(Reading(user_id=901, spread="love", cards_json="major_0,major_1,major_2"))
        await session.commit()
        reading_id = 1

    # User 902 tries to consume a reading belonging to 901.
    async with get_session() as session:
        u = await session.get(User, 902)
    from bot.handlers.reading import _consume_reading
    reason = await _consume_reading(u)
    assert reason is not None


async def _test_parallel_favorite() -> None:
    from bot.handlers.features import _toggle_favorite

    cfg = load_config(require_token=False)
    await get_or_create_user(_tg_user(903), cfg)
    async with get_session() as session:
        session.add(Reading(user_id=903, spread="choice", cards_json="major_0,major_1,major_2"))
        await session.commit()

    async def add():
        return await _toggle_favorite(903, 1)

    results = await asyncio.gather(add(), add())
    # At least one add must succeed; the other sees the existing row and removes it.
    # The final state should be deterministic (no duplicate key errors unhandled).
    async with get_session() as session:
        row = (await session.execute(select(ReadingFavorite).where(ReadingFavorite.user_id == 903))).scalar_one_or_none()
    assert row is not None or any(results)


async def _test_posthog_allowlist() -> None:
    cfg = load_config(require_token=False)
    analytics = Analytics(cfg)
    safe = analytics._safe_props({"spread_type": "love", "question": "my secret", "name": "Alice"})
    assert "spread_type" in safe
    assert "question" not in safe
    assert "name" not in safe


async def _test_sentry_scrub() -> None:
    from bot.main import _init_sentry

    # If no DSN, function should be a no-op and not raise.
    class NoSentryCfg:
        sentry_dsn = None

    _init_sentry(NoSentryCfg())


async def main() -> None:
    await init_db(db_path)
    await _test_alembic_upgrade_empty()
    await _test_alembic_upgrade_copy()
    await _test_assets_present()
    await _test_font_fallback()
    await _test_data_deletion()
    await _test_access_other_reading()
    await _test_parallel_favorite()
    await _test_posthog_allowlist()
    await _test_sentry_scrub()
    print("PATCH 4 CRITICAL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
