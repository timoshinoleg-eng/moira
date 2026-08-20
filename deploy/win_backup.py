"""Interim Windows wrapper for the shared online-backup implementation.

This remains suitable for an owner-controlled beta host, not the supported
Linux production storage boundary.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deploy.backup_restore import BackupRestoreError, create_backup


def _release_sha() -> str:
    configured = os.getenv("MOIRA_RELEASE_SHA", "").strip()
    if configured:
        return configured
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    keep = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    database = Path(os.getenv("DB_PATH", str(ROOT / "moira.db")))
    backup_dir = Path(os.getenv("MOIRA_BACKUP_DIR", str(ROOT / "backups")))
    try:
        artifact = create_backup(
            database,
            backup_dir,
            release_sha=_release_sha(),
            keep=keep,
            rpo_policy_seconds=int(os.getenv("MOIRA_BACKUP_RPO_SECONDS", "86400")),
            allow_source_tree_storage=True,
        )
    except (BackupRestoreError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f"backup failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"backup ok: {artifact.database} "
        f"(manifest: {artifact.manifest.name}, retention: {keep})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
