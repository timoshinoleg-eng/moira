"""Container healthcheck for Moira.

Reads DATABASE_URL directly from the environment: when set it runs `SELECT 1`
against PostgreSQL via asyncpg; otherwise it opens the configured SQLite file.
Exits 0 when the database is reachable, 1 otherwise.

Deliberately does not import bot.config / aiogram so it stays free of token
validation and works regardless of BOT_TOKEN.
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def _check() -> int:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        async def _pg() -> None:
            engine = create_async_engine(database_url)
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            finally:
                await engine.dispose()

        asyncio.run(_pg())
        return 0

    # SQLite: ensure the file is openable/readable.
    from sqlalchemy import create_engine, inspect

    eng = create_engine(f"sqlite:///{os.getenv('DB_PATH', 'moira.db')}")
    try:
        inspect(eng).get_table_names()
    finally:
        eng.dispose()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_check())
    except Exception:  # noqa: BLE001 - a failing healthcheck must exit non-zero
        sys.exit(1)