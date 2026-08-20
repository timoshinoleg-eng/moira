from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from bot.db.database import ALEMBIC_HEAD
from deploy.backup_restore import (
    BackupRestoreError,
    create_backup,
    restore_drill,
    verify_backup,
)

ROOT = Path(__file__).resolve().parents[1]


def _alembic(db_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DB_PATH"] = str(db_path)
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _release_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def representative_database(tmp_path: Path) -> Path:
    database = tmp_path / "representative.db"
    migration = _alembic(database, "upgrade", "head")
    assert migration.returncode == 0, migration.stderr or migration.stdout
    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(database) as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (
                id, username, first_name, language, free_readings,
                promo_readings, unlimited_until, redeemed_promos, birth_date,
                daily_push, last_push_date, push_enabled, push_timezone,
                push_local_time, next_push_at_utc, referred_by,
                referral_variant, last_mirror_week,
                voice_transcription_consent, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                91001,
                None,
                "Synthetic",
                "ru",
                2,
                0,
                None,
                "[]",
                None,
                0,
                None,
                0,
                None,
                None,
                None,
                None,
                "A",
                None,
                0,
                now,
            ),
        )
        assert cursor.rowcount == 1
        reading = connection.execute(
            """
            INSERT INTO readings (
                user_id, spread, cards_json, question, interpretation,
                share_summary, response_mode, input_mode, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                91001,
                "situation",
                '[{"card_name":"The Star","orientation":"upright"}]',
                "Synthetic restore question?",
                "Synthetic interpretation.",
                "Synthetic share summary.",
                "fallback",
                "text",
                now,
            ),
        )
        reading_id = int(reading.lastrowid)
        connection.execute(
            "INSERT INTO reading_favorites (user_id, reading_id, created_at) VALUES (?, ?, ?)",
            (91001, reading_id, now),
        )
        connection.execute(
            """
            INSERT INTO payments (user_id, product, stars, charge_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (91001, "reading_1", 25, "synthetic-restore-charge", "paid", now),
        )
        connection.commit()
    return database


def test_backup_binds_hash_release_retention_and_real_payments_census(
    representative_database: Path, tmp_path: Path
) -> None:
    backup_dir = tmp_path / "protected-backups"
    release_sha = "a" * 40
    base_time = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    artifacts = []
    for offset in range(3):
        instant = base_time + timedelta(seconds=offset)
        artifacts.append(
            create_backup(
                representative_database,
                backup_dir,
                release_sha=release_sha,
                keep=2,
                rpo_policy_seconds=3600,
                now=lambda instant=instant: instant,
            )
        )

    assert not artifacts[0].database.exists()
    assert not artifacts[0].manifest.exists()
    assert artifacts[1].database.is_file()
    assert artifacts[2].database.is_file()
    verified = verify_backup(artifacts[2].database, expected_release_sha=release_sha)
    assert verified["verification"] == "PASS"
    assert verified["rpo_policy_seconds"] == 3600
    assert verified["database"]["row_counts"]["payments"] == 1
    assert verified["database"]["representative_reads"] == {
        "journal_rows": 1,
        "entitled_users": 1,
        "payment_rows": 1,
    }
    assert "payment_ledger" not in json.dumps(verified, sort_keys=True)


def test_backup_rejects_hash_mismatch_and_wrong_release_binding(
    representative_database: Path, tmp_path: Path
) -> None:
    artifact = create_backup(
        representative_database,
        tmp_path / "backups",
        release_sha="b" * 40,
        keep=2,
    )
    with pytest.raises(BackupRestoreError, match="release SHA"):
        verify_backup(artifact.database, expected_release_sha="c" * 40)

    manifest = json.loads(artifact.manifest.read_text(encoding="utf-8"))
    manifest["sha256"] = "0" * 64
    artifact.manifest.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BackupRestoreError, match="hash mismatch"):
        verify_backup(artifact.database)


def test_restore_drill_runs_migrations_startup_and_representative_reads(
    representative_database: Path, tmp_path: Path
) -> None:
    release_sha = _release_sha()
    artifact = create_backup(
        representative_database,
        tmp_path / "backups",
        release_sha=release_sha,
        keep=2,
        rpo_policy_seconds=7200,
    )
    restore_dir = tmp_path / "isolated-restore"
    report = restore_drill(
        artifact.database,
        app_dir=ROOT,
        expected_release_sha=release_sha,
        workdir=restore_dir,
        python=Path(sys.executable),
    )

    assert report["status"] == "PASS"
    assert report["target_release_sha"] == release_sha
    assert report["target_alembic_head"] == ALEMBIC_HEAD
    assert report["integrity_check"] == "ok"
    assert report["foreign_key_failures"] == 0
    assert report["rpo_policy_seconds"] == 7200
    assert report["measured_recovery_point_age_seconds"] >= 0
    assert report["rpo_within_policy"] is True
    assert report["measured_rto_ms"] >= 0
    assert report["row_counts"]["payments"] == 1
    assert report["representative_reads"]["journal_rows"] == 1
    assert report["representative_reads"]["entitled_users"] == 1
    assert report["telegram_smoke"] == "NOT_RUN_EXTERNAL_BOUNDARY"
    assert (restore_dir / "moira.db").is_file()
    assert (restore_dir / "restore-drill-report.json").is_file()


def test_restore_and_rollback_fail_closed_before_overwrite(
    representative_database: Path, tmp_path: Path
) -> None:
    release_sha = _release_sha()
    artifact = create_backup(
        representative_database,
        tmp_path / "backups",
        release_sha=release_sha,
        keep=2,
    )
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    marker = occupied / "keep.txt"
    marker.write_text("preserve", encoding="utf-8")

    with pytest.raises(BackupRestoreError, match="new or empty"):
        restore_drill(
            artifact.database,
            app_dir=ROOT,
            expected_release_sha=release_sha,
            workdir=occupied,
            python=Path(sys.executable),
            operation="rollback-drill",
        )
    assert marker.read_text(encoding="utf-8") == "preserve"

    with pytest.raises(BackupRestoreError, match="target checkout"):
        restore_drill(
            artifact.database,
            app_dir=ROOT,
            expected_release_sha="d" * 40,
            workdir=tmp_path / "unused",
            python=Path(sys.executable),
            operation="rollback-drill",
        )
    assert not (tmp_path / "unused").exists()


def test_restore_rejects_stale_recovery_point_before_copy(
    representative_database: Path, tmp_path: Path
) -> None:
    release_sha = _release_sha()
    old_snapshot = datetime.now(UTC) - timedelta(hours=2)
    artifact = create_backup(
        representative_database,
        tmp_path / "backups",
        release_sha=release_sha,
        keep=2,
        rpo_policy_seconds=60,
        now=lambda: old_snapshot,
    )
    target = tmp_path / "stale-restore"
    with pytest.raises(BackupRestoreError, match="exceeds the configured RPO"):
        restore_drill(
            artifact.database,
            app_dir=ROOT,
            expected_release_sha=release_sha,
            workdir=target,
            python=Path(sys.executable),
        )
    assert not target.exists()


def test_rollback_drill_reports_stale_rpo_but_uses_sha_bound_backup(
    representative_database: Path, tmp_path: Path
) -> None:
    release_sha = _release_sha()
    old_snapshot = datetime.now(UTC) - timedelta(hours=2)
    artifact = create_backup(
        representative_database,
        tmp_path / "backups",
        release_sha=release_sha,
        keep=2,
        rpo_policy_seconds=60,
        now=lambda: old_snapshot,
    )
    report = restore_drill(
        artifact.database,
        app_dir=ROOT,
        expected_release_sha=release_sha,
        workdir=tmp_path / "rollback-target",
        python=Path(sys.executable),
        operation="rollback-drill",
    )
    assert report["status"] == "PASS"
    assert report["operation"] == "rollback-drill"
    assert report["rpo_within_policy"] is False
    assert report["measured_recovery_point_age_seconds"] >= 7200


def test_direct_cli_verify_is_module_safe(
    representative_database: Path, tmp_path: Path
) -> None:
    release_sha = _release_sha()
    artifact = create_backup(
        representative_database,
        tmp_path / "backups",
        release_sha=release_sha,
        keep=2,
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "deploy" / "backup_restore.py"),
            "verify",
            "--backup",
            str(artifact.database),
            "--expected-release-sha",
            release_sha,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["verification"] == "PASS"
