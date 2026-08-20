from __future__ import annotations

import asyncio
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bot.db.database import ALEMBIC_HEAD, close_db, database_revision, init_db
from bot.db.models import Base


ROOT = Path(__file__).resolve().parents[1]


def _alembic(db_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DB_PATH"] = str(db_path)
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_command(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stderr or result.stdout


def test_fresh_database_upgrade_head_check_and_application_startup(
    tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "fresh-release.db"
    _assert_command(_alembic(db_path, "upgrade", "head"))
    _assert_command(_alembic(db_path, "check"))
    assert database_revision(str(db_path)) == ALEMBIC_HEAD

    def forbidden_create_all(*_args, **_kwargs):
        raise AssertionError("application startup must not use create_all")

    monkeypatch.setattr(Base.metadata, "create_all", forbidden_create_all)

    async def start_and_stop() -> None:
        await init_db(str(db_path), require_revision=ALEMBIC_HEAD)
        await close_db()

    asyncio.run(start_and_stop())


def test_real_0005_schema_copy_upgrades_to_head_without_losing_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "upgrade-from-0005.db"
    _assert_command(_alembic(db_path, "upgrade", "0005_growth_attribution"))
    assert database_revision(str(db_path)) == "0005_growth_attribution"

    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO users (
                id, username, first_name, language, free_readings, promo_readings,
                unlimited_until, redeemed_promos, birth_date, daily_push,
                last_push_date, created_at, referred_by, last_mirror_week,
                referral_variant
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (7001, None, "Migration", "ru", 3, 0, None, "[]", None, 0, None, now, None, None, "A"),
        )
        connection.execute(
            """
            INSERT INTO payments (user_id, product, stars, charge_id, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (7001, "reading_1", 25, "migration-charge", now, "paid"),
        )
        connection.execute(
            """
            INSERT INTO llm_usage (
                user_id, spread, model, prompt_version, prompt_tokens,
                completion_tokens, latency_ms, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (7001, "situation", "legacy-model", "legacy", 10, 20, 300, "ok", now),
        )
        connection.commit()

    _assert_command(_alembic(db_path, "upgrade", "head"))
    _assert_command(_alembic(db_path, "check"))
    assert database_revision(str(db_path)) == ALEMBIC_HEAD
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM users WHERE id = 7001").fetchone()[0] == 1
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM payments WHERE charge_id = 'migration-charge'"
            ).fetchone()[0]
            == 1
        )
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "push_deliveries" in tables
        llm_usage_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(llm_usage)").fetchall()
        }
        assert "user_id" not in llm_usage_columns
        assert connection.execute("SELECT COUNT(*) FROM llm_usage").fetchone()[0] == 1


def test_application_startup_rejects_0005_without_repairing_schema(
    tmp_path: Path, monkeypatch
) -> None:
    db_path = tmp_path / "stale-0005.db"
    _assert_command(_alembic(db_path, "upgrade", "0005_growth_attribution"))

    def forbidden_create_all(*_args, **_kwargs):
        raise AssertionError("revision failure must happen before create_all")

    monkeypatch.setattr(Base.metadata, "create_all", forbidden_create_all)
    with pytest.raises(RuntimeError, match="database revision mismatch"):
        asyncio.run(init_db(str(db_path), require_revision=ALEMBIC_HEAD))
    assert database_revision(str(db_path)) == "0005_growth_attribution"


def test_declared_release_head_matches_alembic_head() -> None:
    result = _alembic(Path(os.devnull), "heads")
    _assert_command(result)
    assert result.stdout.split()[0] == ALEMBIC_HEAD
