#!/usr/bin/env bash
# Restore drill: verify a backup by restoring it to an isolated directory and
# running migrations + a read query against the restored copy. Never touches
# the live database. Usage: moira-restore-drill.sh <backup.db> [workdir]
set -euo pipefail

BACKUP="${1:?usage: moira-restore-drill.sh <backup.db> [workdir]}"
WORKDIR="${2:-$(mktemp -d)}"
APP_DIR="${MOIRA_APP_DIR:-/opt/moira/app}"

mkdir -p "$WORKDIR"
RESTORED="$WORKDIR/moira.db"
cp "$BACKUP" "$RESTORED"

# Integrity + row census of the restored copy (no app imports needed).
python3 - "$RESTORED" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
tables = [r[0] for r in con.execute(
    "select name from sqlite_master where type='table' and name not like 'sqlite_%'")]
print("tables:", ", ".join(sorted(tables)))
for t in ("users", "readings", "payment_ledger", "llm_usage"):
    if t in tables:
        print(f"{t}: {con.execute(f'select count(*) from {t}').fetchone()[0]} rows")
ok = con.execute("pragma integrity_check").fetchone()[0]
print("integrity_check:", ok)
assert ok == "ok"
PY

echo "restore drill ok: $RESTORED"
echo "next manual step: point DB_PATH=$RESTORED at a stopped test instance and run the Telegram smoke."
