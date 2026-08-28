from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

_engine = None
_session_factory = None


def _sqlite_pragmas(dbapi_conn, _connection_record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()


async def init_db(db_path: str) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    event.listen(_engine.sync_engine, "connect", _sqlite_pragmas)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
