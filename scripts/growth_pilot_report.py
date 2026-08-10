"""Print a privacy-safe aggregate report for the share-to-reading pilot."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot.config import load_config
from bot.db.database import get_session, init_db
from bot.db.models import Event


EXPERIMENT_EVENTS = ("share_created", "referral_signup", "referral_first_reading")
VARIANTS = ("a", "b", "legacy")


def _variant(props_json: str) -> str:
    try:
        variant = json.loads(props_json or "{}").get("caption_variant")
    except json.JSONDecodeError:
        return "legacy"
    return variant if variant in VARIANTS else "legacy"


async def build_report(db_path: str, min_signups: int) -> dict:
    path = Path(db_path)
    if not path.exists():
        return {
            "status": "database_missing",
            "database": str(path),
            "next_action": "Run the bot migration and collect pilot events before evaluating captions.",
        }

    await init_db(str(path))
    seen: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    async with get_session() as session:
        rows = await session.execute(
            Event.__table__.select().with_only_columns(Event.name, Event.distinct_id, Event.props_json)
        )
        for name, distinct_id, props_json in rows:
            if name in EXPERIMENT_EVENTS:
                seen[name][_variant(props_json)].add(distinct_id)

    variants = {}
    for variant in VARIANTS:
        shares = len(seen["share_created"][variant])
        signups = len(seen["referral_signup"][variant])
        first_readings = len(seen["referral_first_reading"][variant])
        variants[variant] = {
            "share_creators": shares,
            "referred_signups": signups,
            "first_readings": first_readings,
            "signup_per_share": round(signups / shares, 4) if shares else None,
            "reading_per_signup": round(first_readings / signups, 4) if signups else None,
        }

    attributed_signups = sum(variants[variant]["referred_signups"] for variant in ("a", "b"))
    status = "ready_for_directional_review" if attributed_signups >= min_signups else "collecting"
    return {
        "status": status,
        "minimum_referred_signups": min_signups,
        "attributed_referred_signups": attributed_signups,
        "variants": variants,
        "next_action": (
            "Compare A and B on signup_per_share, then verify reading_per_signup before changing the caption."
            if status == "ready_for_directional_review"
            else "Keep the A/B assignment unchanged until the configured referral-signup minimum is reached."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", help="SQLite database path; defaults to DB_PATH from .env")
    parser.add_argument("--min-signups", type=int, default=20)
    args = parser.parse_args()
    if args.min_signups < 1:
        parser.error("--min-signups must be positive")
    cfg = load_config(require_token=False)
    report = asyncio.run(build_report(args.db or cfg.db_path, args.min_signups))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] != "database_missing" else 2


if __name__ == "__main__":
    raise SystemExit(main())
