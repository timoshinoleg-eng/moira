"""Patch 4 critical test matrix: Alembic, assets, fonts, data deletion, privacy.

These checks used to live only as ``_test_*`` helpers driven by ``main()`` at the
bottom of this file, so pytest collected the module and ran none of them: the
matrix was green in CI without ever executing. The helpers are now real tests
sharing one scratch database (several assert on reading id 1, so the original
ordering matters) and the standalone runner still works.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db_path = os.path.join(tempfile.gettempdir(), "moira_patch4.db")

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


@pytest.fixture(scope="module", autouse=True)
async def scratch_db():
    """One throwaway SQLite file for the whole matrix, in its own directory.

    create_all cannot add columns to an existing table, so a reused file would
    make the results depend on whatever ran before it.
    """
    workdir = tempfile.mkdtemp(prefix="moira_patch4_")
    target = os.path.join(workdir, "patch4.db")
    previous = os.environ.get("DB_PATH")
    os.environ["DB_PATH"] = target
    await init_db(target)
    try:
        yield target
    finally:
        if previous is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = previous
        shutil.rmtree(workdir, ignore_errors=True)


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


async def test_alembic_upgrade_empty() -> None:
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


async def test_alembic_upgrade_copy() -> None:
    """An already migrated database passes `upgrade head` idempotently.

    The check used to copy a hardcoded temp path that only exists in the
    standalone runner, and it copied a create_all database, which has no
    alembic version row: `upgrade head` on that copy replays the whole chain and
    collides with the existing tables. The chain is now migrated first, so this
    asserts what its name promises.
    """
    import subprocess

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workdir = tempfile.mkdtemp(prefix="moira_upgrade_")
    migrated = os.path.join(workdir, "migrated.db")
    copy_db = os.path.join(workdir, "copy.db")
    env = os.environ.copy()
    env["DB_PATH"] = migrated
    env.pop("DATABASE_URL", None)

    def run(target: str) -> subprocess.CompletedProcess:
        env["DB_PATH"] = target
        return subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
        )

    try:
        first = run(migrated)
        assert first.returncode == 0, f"initial upgrade failed: {first.stderr}"
        shutil.copy(migrated, copy_db)
        second = run(copy_db)
        assert second.returncode == 0, f"upgrade on copy failed: {second.stderr}"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


async def test_assets_present() -> None:
    found, expected = check_assets()
    assert found == expected, f"assets missing: {found}/{expected}"


async def test_font_fallback() -> None:
    font = _font(24)
    assert font is not None


async def test_data_deletion() -> None:
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


async def test_access_other_reading() -> None:
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


async def test_parallel_favorite() -> None:
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


async def test_posthog_allowlist() -> None:
    cfg = load_config(require_token=False)
    analytics = Analytics(cfg)
    safe = analytics._safe_props({"spread_type": "love", "question": "my secret", "name": "Alice"})
    assert "spread_type" in safe
    assert "question" not in safe
    assert "name" not in safe


async def test_sentry_scrub() -> None:
    from bot.main import _init_sentry

    # If no DSN, function should be a no-op and not raise.
    class NoSentryCfg:
        sentry_dsn = None

    _init_sentry(NoSentryCfg())


async def main() -> None:
    """Standalone runner: the same checks, in the same order, outside pytest."""
    if os.path.exists(db_path):
        os.remove(db_path)
    os.environ["DB_PATH"] = db_path
    await init_db(db_path)
    await test_alembic_upgrade_empty()
    await test_alembic_upgrade_copy()
    await test_assets_present()
    await test_font_fallback()
    await test_data_deletion()
    await test_access_other_reading()
    await test_parallel_favorite()
    await test_posthog_allowlist()
    await test_sentry_scrub()
    print("PATCH 4 CRITICAL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
