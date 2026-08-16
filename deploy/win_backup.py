"""Online SQLite backup for the interim Windows host (Task Scheduler nightly).

Uses the SQLite backup API, so it is safe while the bot is polling.
Usage:  python deploy\\win_backup.py [keep]   (default keep 14 copies)
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "moira.db"
BACKUP_DIR = ROOT / "backups"


def main() -> int:
    keep = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    if not DB.exists():
        print(f"no database at {DB}")
        return 1
    BACKUP_DIR.mkdir(exist_ok=True)
    out = BACKUP_DIR / f"moira-{datetime.now():%Y%m%d-%H%M%S}.db"
    src = sqlite3.connect(DB)
    dst = sqlite3.connect(out)
    src.backup(dst)
    dst.close()
    src.close()
    old = sorted(BACKUP_DIR.glob("moira-*.db"), key=lambda p: p.name)
    for stale in old[:-keep]:
        stale.unlink()
    print(f"backup ok: {out} (retention: {keep})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
