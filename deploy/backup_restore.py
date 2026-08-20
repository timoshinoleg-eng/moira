"""Fail-closed SQLite backup, restore, and rollback drills for Moira.

The production topology remains a single polling process with one SQLite
database.  This module is the shared implementation behind the Linux and
interim Windows wrappers.  It never starts Telegram polling and never reads
application secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Sequence
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.db.database import ALEMBIC_HEAD

BACKUP_SCHEMA_VERSION = 1
FULL_SHA_RE = re.compile(r"[0-9a-f]{40}")
BACKUP_NAME_RE = re.compile(r"moira-[0-9]{8}T[0-9]{6}\.[0-9]{6}Z-[0-9a-f]{8}\.db")
CORE_TABLES = frozenset({"alembic_version", "users", "readings", "payments", "llm_usage"})
HEAD_TABLES = frozenset(
    {
        "alembic_version",
        "events",
        "llm_usage",
        "payments",
        "promo_redemptions",
        "promocodes",
        "push_deliveries",
        "reading_favorites",
        "readings",
        "referrals",
        "users",
    }
)


class BackupRestoreError(RuntimeError):
    """An operational gate failed before a live database could be touched."""


@dataclass(frozen=True)
class BackupArtifact:
    database: Path
    manifest: Path
    report: dict[str, object]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _full_sha(value: str, label: str) -> str:
    normalized = value.strip().lower()
    if FULL_SHA_RE.fullmatch(normalized) is None:
        raise BackupRestoreError(f"{label} must be a full lowercase 40-hex commit SHA")
    return normalized


def _positive_int(value: object, label: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise BackupRestoreError(f"{label} must be a positive integer") from exc
    if parsed <= 0:
        raise BackupRestoreError(f"{label} must be a positive integer")
    return parsed


def _parse_utc(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise BackupRestoreError(f"{label} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise BackupRestoreError(f"{label} must be an ISO-8601 UTC timestamp") from exc
    return parsed.astimezone(UTC)


def _resolved_file(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise BackupRestoreError(f"{label} is not a regular file")
    return resolved


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _ensure_backup_directory(path: Path, *, allow_source_tree: bool = False) -> tuple[Path, str]:
    resolved = path.expanduser().resolve()
    if _is_within(resolved, ROOT) and not allow_source_tree:
        raise BackupRestoreError("production backups must be outside the source tree")
    resolved.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not resolved.is_dir() or resolved.is_symlink():
        raise BackupRestoreError("backup directory must be a real directory, not a symlink")
    if os.name == "posix":
        mode = stat.S_IMODE(resolved.stat().st_mode)
        if mode & 0o077:
            raise BackupRestoreError("backup directory must not be accessible by group or others")
        return resolved, "posix-owner-only-0700"
    return resolved, "windows-local-beta-only"


def _write_json_atomic(path: Path, payload: dict[str, object], *, mode: int = 0o600) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.partial")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if os.name == "posix":
            temporary.chmod(mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _database_connection(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only=ON")
    return connection


def inspect_database(
    path: Path,
    *,
    expected_revision: str | None = None,
    require_head_schema: bool = False,
) -> dict[str, object]:
    """Return a privacy-safe integrity, schema, and representative-read census."""
    database = _resolved_file(path, "database")
    try:
        with closing(_database_connection(database)) as connection:
            integrity_rows = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
            if integrity_rows != ["ok"]:
                raise BackupRestoreError("SQLite integrity_check failed")
            foreign_key_failures = list(connection.execute("PRAGMA foreign_key_check"))
            if foreign_key_failures:
                raise BackupRestoreError("SQLite foreign_key_check failed")
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            required = HEAD_TABLES if require_head_schema else CORE_TABLES
            missing = sorted(required - tables)
            if missing:
                raise BackupRestoreError("required tables missing: " + ", ".join(missing))
            revision_row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
            revision = str(revision_row[0]) if revision_row and revision_row[0] else ""
            if not revision:
                raise BackupRestoreError("database has no Alembic revision")
            if expected_revision is not None and revision != expected_revision:
                raise BackupRestoreError(
                    f"database revision mismatch: expected {expected_revision}, got {revision}"
                )
            counts = {
                table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
                for table in sorted(required - {"alembic_version"})
            }
            representative_reads = {
                "journal_rows": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM readings r "
                        "LEFT JOIN reading_favorites f ON f.reading_id = r.id"
                    ).fetchone()[0]
                ),
                "entitled_users": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM users WHERE free_readings > 0 "
                        "OR promo_readings > 0 OR unlimited_until IS NOT NULL"
                    ).fetchone()[0]
                ),
                "payment_rows": int(connection.execute("SELECT COUNT(*) FROM payments").fetchone()[0]),
            }
    except sqlite3.Error as exc:
        raise BackupRestoreError("database inspection failed") from exc
    return {
        "integrity_check": "ok",
        "foreign_key_failures": 0,
        "alembic_revision": revision,
        "tables": sorted(tables),
        "row_counts": counts,
        "representative_reads": representative_reads,
    }


def _manifest_path(database: Path) -> Path:
    return database.with_name(database.name + ".manifest.json")


def verify_backup(
    backup: Path,
    *,
    expected_release_sha: str | None = None,
) -> dict[str, object]:
    database = _resolved_file(backup, "backup")
    manifest_path = _resolved_file(_manifest_path(database), "backup manifest")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupRestoreError("backup manifest is unreadable") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != BACKUP_SCHEMA_VERSION:
        raise BackupRestoreError("unsupported backup manifest schema")
    if manifest.get("backup_file") != database.name:
        raise BackupRestoreError("backup manifest filename mismatch")
    release_sha = _full_sha(str(manifest.get("release_sha", "")), "manifest release SHA")
    if expected_release_sha is not None:
        expected = _full_sha(expected_release_sha, "expected release SHA")
        if release_sha != expected:
            raise BackupRestoreError("backup release SHA does not match rollback target")
    actual_hash = _sha256(database)
    if manifest.get("sha256") != actual_hash:
        raise BackupRestoreError("backup hash mismatch")
    if manifest.get("bytes") != database.stat().st_size:
        raise BackupRestoreError("backup size mismatch")
    completed_at = _parse_utc(manifest.get("completed_at_utc"), "backup completion time")
    rpo_policy_seconds = _positive_int(manifest.get("rpo_policy_seconds"), "RPO policy")
    if database.parent.is_symlink():
        raise BackupRestoreError("backup directory must not be a symlink")
    if os.name == "posix" and stat.S_IMODE(database.parent.stat().st_mode) & 0o077:
        raise BackupRestoreError("backup storage permissions are not owner-only")
    database_report = inspect_database(database)
    if manifest.get("alembic_revision") != database_report["alembic_revision"]:
        raise BackupRestoreError("backup manifest revision mismatch")
    return {
        "verification": "PASS",
        "backup_file": database.name,
        "manifest_file": manifest_path.name,
        "sha256": actual_hash,
        "bytes": database.stat().st_size,
        "release_sha": release_sha,
        "completed_at_utc": _iso_utc(completed_at),
        "rpo_policy_seconds": rpo_policy_seconds,
        "database": database_report,
    }


def _retention_candidates(backup_dir: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in backup_dir.iterdir()
            if path.is_file() and not path.is_symlink() and BACKUP_NAME_RE.fullmatch(path.name)
        ),
        key=lambda path: path.name,
        reverse=True,
    )


def apply_retention(backup_dir: Path, *, keep: int) -> list[str]:
    if keep < 2:
        raise BackupRestoreError("retention must preserve at least two backups")
    removed: list[str] = []
    for database in _retention_candidates(backup_dir)[keep:]:
        resolved = database.resolve()
        if resolved.parent != backup_dir.resolve():
            raise BackupRestoreError("retention candidate escaped the backup directory")
        manifest = _manifest_path(resolved)
        if not manifest.is_file() or manifest.is_symlink():
            continue
        verify_backup(resolved)
        resolved.unlink()
        manifest.unlink()
        removed.append(resolved.name)
    return removed


def create_backup(
    source: Path,
    backup_dir: Path,
    *,
    release_sha: str,
    keep: int = 14,
    rpo_policy_seconds: int = 86_400,
    allow_source_tree_storage: bool = False,
    now: Callable[[], datetime] = _utc_now,
) -> BackupArtifact:
    """Create, verify, bind, and retain an online SQLite backup."""
    started_at = now()
    started = time.monotonic()
    database = _resolved_file(source, "source database")
    release = _full_sha(release_sha, "release SHA")
    if keep < 2:
        raise BackupRestoreError("retention must preserve at least two backups")
    if rpo_policy_seconds <= 0:
        raise BackupRestoreError("RPO policy must be positive")
    destination_dir, storage_protection = _ensure_backup_directory(
        backup_dir, allow_source_tree=allow_source_tree_storage
    )
    source_report = inspect_database(database)
    stamp = started_at.astimezone(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    filename = f"moira-{stamp}-{uuid4().hex[:8]}.db"
    output = destination_dir / filename
    partial = destination_dir / f".{filename}.{uuid4().hex}.partial"
    if output.resolve() == database.resolve():
        raise BackupRestoreError("backup destination overlaps the source database")
    try:
        source_uri = f"file:{database.resolve().as_posix()}?mode=ro"
        with closing(sqlite3.connect(source_uri, uri=True)) as source_connection:
            with closing(sqlite3.connect(partial)) as destination_connection:
                source_connection.backup(destination_connection)
        if os.name == "posix":
            partial.chmod(0o600)
        inspected = inspect_database(partial)
        if inspected["alembic_revision"] != source_report["alembic_revision"]:
            raise BackupRestoreError("backup revision changed during online copy")
        duration_ms = int((time.monotonic() - started) * 1000)
        report: dict[str, object] = {
            "schema_version": BACKUP_SCHEMA_VERSION,
            "created_at_utc": _iso_utc(started_at),
            "completed_at_utc": _iso_utc(now()),
            "backup_file": output.name,
            "release_sha": release,
            "alembic_revision": inspected["alembic_revision"],
            "sha256": _sha256(partial),
            "bytes": partial.stat().st_size,
            "backup_duration_ms": duration_ms,
            "rpo_policy_seconds": rpo_policy_seconds,
            "storage_protection": storage_protection,
            "integrity_check": inspected["integrity_check"],
            "foreign_key_failures": inspected["foreign_key_failures"],
            "row_counts": inspected["row_counts"],
            "representative_reads": inspected["representative_reads"],
        }
        partial.replace(output)
        try:
            _write_json_atomic(_manifest_path(output), report)
        except Exception:
            output.unlink(missing_ok=True)
            raise
        verified = verify_backup(output, expected_release_sha=release)
        removed = apply_retention(destination_dir, keep=keep)
        result = dict(report)
        result["verification"] = verified["verification"]
        result["retention_keep"] = keep
        result["retention_removed"] = removed
        return BackupArtifact(output, _manifest_path(output), result)
    except sqlite3.Error as exc:
        raise BackupRestoreError("SQLite online backup failed") from exc
    finally:
        partial.unlink(missing_ok=True)


def _git_head(app_dir: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(app_dir), "rev-parse", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise BackupRestoreError("target application directory is not an exact Git checkout")
    return _full_sha(result.stdout.strip(), "target checkout SHA")


def _run_checked(command: Sequence[str], *, cwd: Path, env: dict[str, str], label: str) -> None:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise BackupRestoreError(f"{label} failed")


def _target_alembic_head(app_dir: Path, python: Path) -> str:
    result = subprocess.run(
        [str(python), "-c", "from bot.db.database import ALEMBIC_HEAD; print(ALEMBIC_HEAD)"],
        cwd=app_dir,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise BackupRestoreError("target application Alembic head is unreadable")
    return result.stdout.strip()


APP_STARTUP_SMOKE = """
import asyncio
import sys
from bot.db.database import close_db, init_db

async def main():
    await init_db(sys.argv[1], require_revision=sys.argv[2])
    await close_db()

asyncio.run(main())
"""


def _new_restore_directory(workdir: Path | None) -> Path:
    if workdir is None:
        import tempfile

        return Path(tempfile.mkdtemp(prefix="moira-restore-", suffix="-isolated")).resolve()
    target = workdir.expanduser().resolve()
    if target.exists():
        if not target.is_dir() or any(target.iterdir()):
            raise BackupRestoreError("restore directory must be new or empty")
    else:
        target.mkdir(mode=0o700, parents=True)
    if target.is_symlink() or _is_within(target, ROOT):
        raise BackupRestoreError("restore directory must be isolated outside the source tree")
    return target


def restore_drill(
    backup: Path,
    *,
    app_dir: Path,
    expected_release_sha: str,
    workdir: Path | None = None,
    python: Path | None = None,
    operation: str = "restore-drill",
    now: Callable[[], datetime] = _utc_now,
) -> dict[str, object]:
    """Restore to an isolated directory and exercise migrations and app startup."""
    started = time.monotonic()
    expected = _full_sha(expected_release_sha, "expected release SHA")
    application = app_dir.expanduser().resolve()
    if not application.is_dir():
        raise BackupRestoreError("target application directory is missing")
    if _git_head(application) != expected:
        raise BackupRestoreError("target checkout does not match the expected release SHA")
    backup_report = verify_backup(backup, expected_release_sha=expected)
    recovery_point_age_seconds = max(
        0.0,
        (now() - _parse_utc(backup_report["completed_at_utc"], "backup completion time")).total_seconds(),
    )
    rpo_within_policy = recovery_point_age_seconds <= int(backup_report["rpo_policy_seconds"])
    if operation == "restore-drill" and not rpo_within_policy:
        raise BackupRestoreError("backup recovery point exceeds the configured RPO policy")
    source = _resolved_file(backup, "backup")
    target_dir = _new_restore_directory(workdir)
    if _is_within(target_dir, application):
        raise BackupRestoreError("restore directory must be outside the target checkout")
    restored = target_dir / "moira.db"
    if restored.exists():
        raise BackupRestoreError("restore target already exists")
    shutil.copy2(source, restored)
    if os.name == "posix":
        restored.chmod(0o600)
    if _sha256(restored) != backup_report["sha256"]:
        raise BackupRestoreError("restored copy hash mismatch before migrations")
    interpreter = (python or Path(sys.executable)).expanduser().resolve()
    if not interpreter.is_file():
        raise BackupRestoreError("Python interpreter for the target release is missing")
    target_head = _target_alembic_head(application, interpreter)
    environment = os.environ.copy()
    environment["DB_PATH"] = str(restored)
    _run_checked(
        [str(interpreter), "-m", "alembic", "upgrade", "head"],
        cwd=application,
        env=environment,
        label="Alembic upgrade on restored copy",
    )
    _run_checked(
        [str(interpreter), "-m", "alembic", "check"],
        cwd=application,
        env=environment,
        label="Alembic check on restored copy",
    )
    _run_checked(
        [str(interpreter), "-c", APP_STARTUP_SMOKE, str(restored), target_head],
        cwd=application,
        env=environment,
        label="application startup against restored copy",
    )
    post_restore = inspect_database(
        restored, expected_revision=target_head, require_head_schema=(target_head == ALEMBIC_HEAD)
    )
    rto_ms = int((time.monotonic() - started) * 1000)
    report: dict[str, object] = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "operation": operation,
        "status": "PASS",
        "target_release_sha": expected,
        "target_alembic_head": target_head,
        "backup_file": source.name,
        "backup_sha256": backup_report["sha256"],
        "restored_database": restored.name,
        "restored_sha256_after_migrations": _sha256(restored),
        "rpo_policy_seconds": backup_report["rpo_policy_seconds"],
        "measured_recovery_point_age_seconds": round(recovery_point_age_seconds, 3),
        "rpo_within_policy": rpo_within_policy,
        "measured_rto_ms": rto_ms,
        "integrity_check": post_restore["integrity_check"],
        "foreign_key_failures": post_restore["foreign_key_failures"],
        "row_counts": post_restore["row_counts"],
        "representative_reads": post_restore["representative_reads"],
        "telegram_smoke": "NOT_RUN_EXTERNAL_BOUNDARY",
    }
    _write_json_atomic(target_dir / f"{operation}-report.json", report)
    return report


def _print_report(report: dict[str, object]) -> None:
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Moira fail-closed backup and restore operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup", help="create an online backup before release or nightly")
    backup.add_argument("--db", required=True)
    backup.add_argument("--backup-dir", required=True)
    backup.add_argument("--release-sha", required=True)
    backup.add_argument("--keep", type=int, default=14)
    backup.add_argument("--rpo-seconds", type=int, default=86_400)
    backup.add_argument("--allow-source-tree-storage", action="store_true")

    verify = subparsers.add_parser("verify", help="verify a bound backup without restoring it")
    verify.add_argument("--backup", required=True)
    verify.add_argument("--expected-release-sha")

    for name in ("restore-drill", "rollback-drill"):
        drill = subparsers.add_parser(name)
        drill.add_argument("--backup", required=True)
        drill.add_argument("--app-dir", required=True)
        drill.add_argument("--expected-release-sha", required=True)
        drill.add_argument("--workdir")
        drill.add_argument("--python")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "backup":
            artifact = create_backup(
                Path(args.db),
                Path(args.backup_dir),
                release_sha=args.release_sha,
                keep=args.keep,
                rpo_policy_seconds=args.rpo_seconds,
                allow_source_tree_storage=args.allow_source_tree_storage,
            )
            _print_report(artifact.report)
        elif args.command == "verify":
            _print_report(
                verify_backup(
                    Path(args.backup), expected_release_sha=args.expected_release_sha
                )
            )
        else:
            _print_report(
                restore_drill(
                    Path(args.backup),
                    app_dir=Path(args.app_dir),
                    expected_release_sha=args.expected_release_sha,
                    workdir=Path(args.workdir) if args.workdir else None,
                    python=Path(args.python) if args.python else None,
                    operation=args.command,
                )
            )
        return 0
    except BackupRestoreError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
