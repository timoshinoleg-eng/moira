#!/usr/bin/env bash
# Online SQLite backup with hash-bound manifest and retention. Safe while the
# bot is running. Usage: moira-backup.sh [backup_dir]
set -euo pipefail

BACKUP_DIR="${1:-/var/backups/moira}"
KEEP="${MOIRA_BACKUP_KEEP:-14}"
DB_PATH="${MOIRA_DB_PATH:-/var/lib/moira/moira.db}"
APP_DIR="${MOIRA_APP_DIR:-/opt/moira/app}"
TOOL_APP_DIR="${MOIRA_TOOL_APP_DIR:-$APP_DIR}"
PYTHON_BIN="${MOIRA_PYTHON:-$TOOL_APP_DIR/.venv/bin/python}"
RPO_SECONDS="${MOIRA_BACKUP_RPO_SECONDS:-86400}"
RELEASE_SHA="${MOIRA_RELEASE_SHA:-}"

if [[ -z "$RELEASE_SHA" ]]; then
  RELEASE_SHA="$(git -C "$APP_DIR" rev-parse HEAD)"
fi
if [[ "$(git -C "$APP_DIR" rev-parse HEAD)" != "$RELEASE_SHA" ]]; then
  echo "MOIRA_RELEASE_SHA does not match deployed HEAD" >&2
  exit 1
fi
if [[ -n "$(git -C "$APP_DIR" status --porcelain=v1 --untracked-files=no)" ]]; then
  echo "deployed tracked files are dirty" >&2
  exit 1
fi

exec "$PYTHON_BIN" "$TOOL_APP_DIR/deploy/backup_restore.py" backup \
  --db "$DB_PATH" \
  --backup-dir "$BACKUP_DIR" \
  --release-sha "$RELEASE_SHA" \
  --keep "$KEEP" \
  --rpo-seconds "$RPO_SECONDS"
