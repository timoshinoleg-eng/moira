"""Container healthcheck for Moira.

Checks that the process can attach to the configured database. When
DATABASE_URL is set it runs SELECT 1 against PostgreSQL; otherwise it touches
the configured SQLite file. Exits 0 when healthy, 1 otherwise.

This must never emit user data.
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import create_engine, inspect, text


def _check() -> int:
    from bot.config import load_config

    cfg = load_config(require_token=False)

    if cfg.database_url:
        from sqlalchemy.ext.asyncio import create_async_engine

        async def _pg() -> None:
            engine = create_async_engine(cfg.database_url)
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            finally:
                await engine.dispose()

        asyncio.run(_pg())
        return 0

    # SQLite: ensure the file is openable/readable.
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