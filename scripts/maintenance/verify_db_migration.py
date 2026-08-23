"""Verify a SQLite->PostgreSQL data migration.

Counts every user table on each side and compares row counts, then compares a
deterministic payment-ledger checksum (count, summed stars, and status
distribution by charge_id) so that no payment is lost during the migration.

Designed to be backend-agnostic: pass any two SQLAlchemy connection strings.

Usage:
    python scripts/maintenance/verify_db_migration.py \
        --source sqlite+aiosqlite:///moira.db \
        --target postgresql+asyncpg://moira:moira@localhost:5432/moira

Exit code 0 when all tables match and the ledger checksums are equal.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Tables that carry user-visible data and must be verified post-migration.
# alembic_version is metadata and intentionally excluded.
REQUIRED_TABLES = (
    "users",
    "readings",
    "payments",
    "promocodes",
    "promo_redemptions",
    "referrals",
    "reading_favorites",
    "llm_usage",
    "events",
    "push_deliveries",
)

LEDGER_TABLES = ("payments",)


@dataclass(frozen=True)
class TableCounts:
    rows: dict[str, int]

    def same_as(self, other: TableCounts) -> bool:
        missing = set(self.rows) ^ set(other.rows)
        if missing:
            return False
        for k in self.rows:
            if self.rows[k] != other.rows[k]:
                return False
        return True


async def _table_rows(url: str) -> dict[str, int]:
    engine = create_async_engine(url)
    counts: dict[str, int] = {}
    try:
        async with engine.connect() as conn:
            for t in REQUIRED_TABLES:
                try:
                    n = await conn.scalar(text(f"SELECT count(*) FROM {t}"))
                    counts[t] = int(n)
                except Exception:  # noqa: BLE001 - table missing on this side
                    continue
    finally:
        await engine.dispose()
    return counts


async def _ledger_checksum(url: str) -> str:
    """Deterministic digest over payments content (identity + amounts + status)."""
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT user_id, product, stars, charge_id, status "
                        "FROM payments ORDER BY id"
                    )
                )
            ).all()
    finally:
        await engine.dispose()
    parts = [f"{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}" for r in rows]
    payload = "\n".join(parts)
    import hashlib

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def main() -> int:
    ap = argparse.ArgumentParser(description="Verify SQLite->PostgreSQL migration")
    ap.add_argument("--source", required=True, help="source SQLAlchemy URL (SQLite)")
    ap.add_argument("--target", required=True, help="target SQLAlchemy URL (PostgreSQL)")
    args = ap.parse_args()

    src_counts = await _table_rows(args.source)
    tgt_counts = await _table_rows(args.target)

    ok = True
    for t in REQUIRED_TABLES:
        s = src_counts.get(t, "MISSING")
        g = tgt_counts.get(t, "MISSING")
        same = s == g
        ok = ok and same
        print(f"{t:20} source={s!s:8} target={g!s:8} {'OK' if same else 'MISMATCH'}")

    src_ledger = await _ledger_checksum(args.source)
    tgt_ledger = await _ledger_checksum(args.target)
    ledger_ok = src_ledger == tgt_ledger
    ok = ok and ledger_ok
    print(f"ledger(source) = {src_ledger[:16]}...")
    print(f"ledger(target) = {tgt_ledger[:16]}...")
    print(f"ledger MATCH: {ledger_ok}")

    if not ok:
        print("VERIFY: FAILED")
        return 1
    print("VERIFY: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))