"""PostgreSQL integration test (stage 3).

Runs Alembic migrations on a real PostgreSQL 16 (via testcontainers), then
exercises init_db(database_url), a basic CRUD round-trip and the payment ledged
uniqueness that matters for refund idempotency.

Skipped when Docker / a PostgreSQL container is not available (the default
local run stays SQLite-only and does not require containers).
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

pytestmark = [pytest.mark.asyncio, pytest.mark.postgres]

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pg_url() -> str | None:
    from testcontainers.postgres import PostgresContainer

    container = PostgresContainer("postgres:16")
    try:
        container.start()
    except Exception:  # noqa: BLE001
        pytest.skip("Docker/PostgreSQL unavailable")
        return None
    try:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        user = container.username or "test"
        password = container.password or "test"
        dbname = container.dbname or "test"
        yield f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"
    finally:
        container.stop()


async def _run_alembic(url: str) -> None:
    env = dict(os.environ)
    env["DATABASE_URL"] = url
    env.pop("DB_PATH", None)
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        "upgrade",
        "head",
        cwd=str(ROOT),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    assert proc.returncode == 0, f"alembic upgrade failed:\n{out.decode(errors='replace')}"


async def _alembic_check(url: str) -> None:
    env = dict(os.environ)
    env["DATABASE_URL"] = url
    env.pop("DB_PATH", None)
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        "check",
        cwd=str(ROOT),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    assert proc.returncode == 0, f"alembic check failed:\n{out.decode(errors='replace')}"


async def test_pg_migrations_apply_clean(pg_url: str | None) -> None:
    if pg_url is None:
        pytest.skip("no PostgreSQL")
    await _run_alembic(pg_url)
    await _alembic_check(pg_url)


async def test_pg_crud_and_ledger(pg_url: str | None) -> None:
    if pg_url is None:
        pytest.skip("no PostgreSQL")
    await _run_alembic(pg_url)

    from bot.db.database import close_db, get_session, init_db
    from bot.db.models import Payment, User

    await init_db(pg_url)
    try:
        async with get_session() as s:
            s.add(User(id=1, language="ru", free_readings=5))
            s.add(Payment(user_id=1, product="reading_1", stars=25, charge_id="pg_chg_1", status="paid"))
            await s.commit()

        # unique charge_id must be enforced by the DB even across sessions
        with pytest.raises(IntegrityError):
            async with get_session() as s:
                s.add(Payment(user_id=1, product="reading_1", stars=25, charge_id="pg_chg_1", status="paid"))
                await s.commit()

        async with get_session() as s:
            n = await s.scalar(select(func.count()).select_from(Payment).where(Payment.charge_id == "pg_chg_1"))
            assert n == 1, "duplicate charge_id accepted on PostgreSQL"

        async with get_session() as s:
            u = await s.get(User, 1)
            assert u is not None and u.free_readings == 5
    finally:
        await close_db()