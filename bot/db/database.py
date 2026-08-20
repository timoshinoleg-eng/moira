from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

_engine = None
_session_factory = None
ALEMBIC_HEAD = "0009_llm_usage_privacy"


def _sqlite_pragmas(dbapi_conn, _connection_record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()


def database_revision(db_path: str) -> str:
    """Read the exact Alembic revision without creating or repairing a database."""
    path = Path(db_path).expanduser()
    if db_path == ":memory:" or not path.is_file():
        raise RuntimeError("database file is missing; run 'alembic upgrade head' before startup")
    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    except sqlite3.Error as exc:
        raise RuntimeError("database has no readable Alembic revision") from exc
    if row is None or not isinstance(row[0], str) or not row[0]:
        raise RuntimeError("database has no Alembic revision")
    return row[0]


async def init_db(db_path: str, *, require_revision: str | None = None) -> None:
    """Initialize sessions, using Alembic as the application schema authority.

    Tests and isolated synthetic evaluators may omit ``require_revision`` to
    bootstrap disposable metadata. The application entry point always supplies
    the release head and therefore never calls ``create_all``.
    """
    global _engine, _session_factory
    if require_revision is not None:
        actual_revision = database_revision(db_path)
        if actual_revision != require_revision:
            raise RuntimeError(
                f"database revision mismatch: expected {require_revision}, got {actual_revision}"
            )
    _engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    event.listen(_engine.sync_engine, "connect", _sqlite_pragmas)
    if require_revision is None:
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
