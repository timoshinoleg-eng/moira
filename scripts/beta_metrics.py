"""Beta metrics: feedback quality, conversion funnel, d7 return.

Reads the application DB (DATABASE_URL takes precedence, else DB_PATH) and
prints a plain-text report. Used during the invite-only beta to decide which
model/prompt to keep (issue #19).

Usage:
    python scripts/beta_metrics.py [--json reports/beta_metrics.json]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Sequence

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import load_config
from bot.db.database import close_db, get_session, init_db
from bot.db.models import Event, LlmUsage, Reading, ReadingFeedback

# Days after the first reading that count as a "return" for retention.
RETURN_WINDOW_DAYS = 7


def _rate(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


async def feedback_totals(session: AsyncSession) -> dict[str, Any]:
    """Overall positive/negative feedback counts and positive rate."""
    rows = (
        await session.execute(
            select(ReadingFeedback.value, func.count()).group_by(ReadingFeedback.value)
        )
    ).all()
    counts = {value: int(n) for value, n in rows}
    positive = counts.get("positive", 0)
    negative = counts.get("negative", 0)
    return {
        "positive": positive,
        "negative": negative,
        "positive_rate": _rate(positive, positive + negative),
    }


async def feedback_by(session: AsyncSession, dimension: str) -> dict[str, Any]:
    """Positive rate grouped by ``prompt_version``, ``model`` or ``spread``."""
    if dimension == "spread":
        stmt = (
            select(Reading.spread, ReadingFeedback.value, func.count())
            .join(Reading, Reading.id == ReadingFeedback.reading_id)
            .group_by(Reading.spread, ReadingFeedback.value)
        )
    elif dimension in ("prompt_version", "model"):
        column = LlmUsage.prompt_version if dimension == "prompt_version" else LlmUsage.model
        stmt = (
            select(column, ReadingFeedback.value, func.count())
            .join(LlmUsage, LlmUsage.generation_id == ReadingFeedback.generation_id)
            .where(ReadingFeedback.generation_id.is_not(None))
            .group_by(column, ReadingFeedback.value)
        )
    else:
        raise ValueError(f"unknown dimension: {dimension}")

    buckets: dict[str, dict[str, int]] = {}
    for bucket, value, n in (await session.execute(stmt)).all():
        entry = buckets.setdefault(str(bucket), {"positive": 0, "negative": 0})
        entry[value] = entry.get(value, 0) + int(n)
    return {
        name: {**counts, "positive_rate": _rate(counts["positive"], counts["positive"] + counts["negative"])}
        for name, counts in buckets.items()
    }


async def funnel(session: AsyncSession) -> dict[str, Any]:
    """Distinct-user funnel: spread_started -> spread_completed."""
    rows = (
        await session.execute(
            select(Event.name, func.count(func.distinct(Event.distinct_id)))
            .where(Event.name.in_(("spread_started", "spread_completed")))
            .group_by(Event.name)
        )
    ).all()
    started = completed = 0
    for name, n in rows:
        if name == "spread_started":
            started = int(n)
        elif name == "spread_completed":
            completed = int(n)
    return {
        "spread_started_users": started,
        "spread_completed_users": completed,
        "conversion": _rate(completed, started),
    }


async def retention(session: AsyncSession) -> dict[str, Any]:
    """Share of users who make another reading >= RETURN_WINDOW_DAYS after their first."""
    rows = (await session.execute(select(Reading.user_id, Reading.created_at))).all()
    per_user: dict[int, list[datetime]] = {}
    for user_id, created in rows:
        moment = _as_utc(created)
        if moment is not None:
            per_user.setdefault(user_id, []).append(moment)
    returned = 0
    for moments in per_user.values():
        first = min(moments)
        if any((moment - first).days >= RETURN_WINDOW_DAYS for moment in moments):
            returned += 1
    active = len(per_user)
    return {
        "active_users": active,
        "d7_return_users": returned,
        "d7_return_rate": _rate(returned, active),
    }


async def collect(session: AsyncSession) -> dict[str, Any]:
    return {
        "feedback": await feedback_totals(session),
        "feedback_by_prompt_version": await feedback_by(session, "prompt_version"),
        "feedback_by_model": await feedback_by(session, "model"),
        "feedback_by_spread": await feedback_by(session, "spread"),
        "funnel": await funnel(session),
        "retention": await retention(session),
    }


def _fmt_rate(rate: float | None) -> str:
    return "n/a" if rate is None else f"{rate * 100:.1f}%"


def render(report: dict[str, Any]) -> str:
    lines: list[str] = ["# Moira beta metrics", ""]

    fb = report["feedback"]
    lines.append(f"Feedback: +{fb['positive']} / -{fb['negative']}  (positive: {_fmt_rate(fb['positive_rate'])})")

    for label, key in (
        ("By prompt version", "feedback_by_prompt_version"),
        ("By model", "feedback_by_model"),
        ("By spread", "feedback_by_spread"),
    ):
        lines.append("")
        lines.append(f"{label}:")
        buckets = report[key]
        if not buckets:
            lines.append("  (no data)")
        for name in sorted(buckets):
            b = buckets[name]
            lines.append(
                f"  {name:<28} +{b['positive']:<5} -{b['negative']:<5} positive {_fmt_rate(b['positive_rate'])}"
            )

    fn = report["funnel"]
    lines.append("")
    lines.append(
        f"Funnel: started {fn['spread_started_users']} -> completed {fn['spread_completed_users']} "
        f"(conversion {_fmt_rate(fn['conversion'])})"
    )

    rt = report["retention"]
    lines.append(
        f"Retention: active users {rt['active_users']}, returned after {RETURN_WINDOW_DAYS}d "
        f"{rt['d7_return_users']} ({_fmt_rate(rt['d7_return_rate'])})"
    )
    return "\n".join(lines)


async def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", dest="json_path", default=None, help="write raw metrics as JSON")
    args = parser.parse_args(argv)

    cfg = load_config(require_token=False)
    await init_db(cfg.database_url or cfg.db_path)
    try:
        async with get_session() as session:
            report = await collect(session)
    finally:
        await close_db()

    print(render(report))
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        print(f"\nJSON written to {args.json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
