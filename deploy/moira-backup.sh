#!/usr/bin/env bash
# Online SQLite backup with retention. Safe while the bot is running.
# Usage: moira-backup.sh [backup_dir]   (default /var/backups/moira, keep 14)
set -euo pipefail

BACKUP_DIR="${1:-/var/backups/moira}"
KEEP="${MOIRA_BACKUP_KEEP:-14}"
DB_PATH="${MOIRA_DB_PATH:-/var/lib/moira/moira.db}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/moira-$STAMP.db"

python3 - "$DB_PATH" "$OUT" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close()
src.close()
print(sys.argv[2])
PY

ls -1t "$BACKUP_DIR"/moira-*.db | tail -n +$((KEEP + 1)) | xargs -r rm -f
echo "backup ok: $OUT (retention: $KEEP)"
