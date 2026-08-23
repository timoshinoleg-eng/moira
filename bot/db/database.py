from __future__ import annotations

import os

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None

_PG_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5") or "5")
_PG_MAX_OVERFLOW = int(os.getenv("DB_POOL_MAX_OVERFLOW", "10") or "10")


def _sqlite_pragmas(dbapi_conn, _connection_record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()


def _is_url(value: str) -> bool:
    """True when value looks like a SQLAlchemy connect string (scheme://...)."""
    return "://" in value


def _build_engine(target: str) -> AsyncEngine:
    if _is_url(target) and target.startswith("postgresql"):
        # asyncpg PostgreSQL: pooling + healthcheck hook.
        engine = create_async_engine(
            target,
            pool_size=_PG_POOL_SIZE,
            max_overflow=_PG_MAX_OVERFLOW,
            pool_pre_ping=True,
        )
        return engine
    if _is_url(target):
        return create_async_engine(target)
    # Plain path → SQLite (dev/tests), with WAL pragmas only here.
    engine = create_async_engine(f"sqlite+aiosqlite:///{target}")
    event.listen(engine.sync_engine, "connect", _sqlite_pragmas)
    return engine


async def _sqlite_create_all(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _pg_healthcheck(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def init_db(target: str) -> None:
    """Initialize engine/session factory from a URL or an SQLite file path."""
    global _engine, _session_factory
    _engine = _build_engine(target)
    if _engine.dialect.name == "postgresql":
        await _pg_healthcheck(_engine)
        # PostgreSQL schema is applied via Alembic (not create_all) in CI/prod.
    else:
        # SQLite dev/test keeps the historical create_all behaviour.
        await _sqlite_create_all(_engine)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def close_db() -> None:
    """Dispose the current async engine during application or test shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_session() -> AsyncSession:
    if _session_factory is None:
        raise RuntimeError("Database is not initialized; call init_db() first.")
    return _session_factory()
