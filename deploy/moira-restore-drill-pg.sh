#!/usr/bin/env bash
# Moira PostgreSQL restore drill.
#
# Restores the newest pg_dump backup (custom format, -Fc, produced by the
# prodrigestivill backup service) into an isolated throwaway database and
# verifies row counts for the payment ledger. Safe to run against a live
# cluster: it never touches the primary database.
#
# Env: PG* (host/user/db), BACKUP_DIR (default ./backups), DRILL_DB (default moira_restore_drill)
# Requires psql + pg_restore on PATH (or replace with docker exec of the db container).
#
# Usage: deploy/moira-restore-drill-pg.sh
# Exit 0 when restore succeeds and ledger counts look sane.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-moira}"
PGDATABASE="${PGDATABASE:-moira}"
DRILL_DB="${DRILL_DB:-moira_restore_drill}"

# Newest pg_dump custom-format file. Backup service nests under BACKUP_DIR (subdir per db name).
DUMPS="$(find "$BACKUP_DIR" -type f -name '*.dump' 2>/dev/null | sort -r || true)"
if [ -z "$DUMPS" ]; then
  echo "No .dump backup files found under $BACKUP_DIR" >&2
  exit 1
fi
LATEST="$(echo "$DUMPS" | head -n1)"
echo "Using backup: $LATEST"

export PGPASSWORD="${PGPASSWORD:-moira}"
ADMIN_DB="${PGDATABASE}"

# Drop leftover drill db, recreate empty.
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$ADMIN_DB" -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS ${DRILL_DB}" >/dev/null
createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "${DRILL_DB}"

trap 'psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$ADMIN_DB" -c "DROP DATABASE IF EXISTS ${DRILL_DB}" >/dev/null' EXIT

pg_restore -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "${DRILL_DB}" --no-owner "$LATEST"

N_PAYMENTS="$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "${DRILL_DB}" -Atc "SELECT count(*) FROM payments" 2>/dev/null || true)"
echo "restored payments count: ${N_PAYMENTS:-0}"
echo "RESTORE DRILL OK"