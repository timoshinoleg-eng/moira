#!/usr/bin/env bash
# Restore drill: verify a bound backup in an isolated directory, run Alembic
# upgrade/check, application startup, and privacy-safe representative reads.
# Never touches the live database.
# Usage: moira-restore-drill.sh <backup.db> <expected-release-sha> [workdir]
set -euo pipefail

BACKUP="${1:?usage: moira-restore-drill.sh <backup.db> <expected-release-sha> [workdir]}"
EXPECTED_SHA="${2:?usage: moira-restore-drill.sh <backup.db> <expected-release-sha> [workdir]}"
WORKDIR="${3:-}"
APP_DIR="${MOIRA_APP_DIR:-/opt/moira/app}"
TOOL_APP_DIR="${MOIRA_TOOL_APP_DIR:-/opt/moira/app}"
PYTHON_BIN="${MOIRA_PYTHON:-$TOOL_APP_DIR/.venv/bin/python}"
OPERATION="${MOIRA_RESTORE_OPERATION:-restore-drill}"

case "$OPERATION" in
  restore-drill|rollback-drill) ;;
  *) echo "unsupported MOIRA_RESTORE_OPERATION" >&2; exit 2 ;;
esac

args=(
  "$PYTHON_BIN" "$TOOL_APP_DIR/deploy/backup_restore.py" "$OPERATION"
  --backup "$BACKUP"
  --app-dir "$APP_DIR"
  --expected-release-sha "$EXPECTED_SHA"
  --python "$PYTHON_BIN"
)
if [[ -n "$WORKDIR" ]]; then
  args+=(--workdir "$WORKDIR")
fi
exec "${args[@]}"
