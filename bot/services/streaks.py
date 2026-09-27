"""Ritual streaks: the return loop that turns a one-off reading into a daily habit.

A *ritual day* is any local calendar day on which the user did something
meaningful with Moira — finished a reading, opened the altar, completed the
arcana quiz or saved a note. The streak counts consecutive ritual days.

Two decisions shape the design:

* **Local days, not UTC days.** A streak that rolls over at 00:00 UTC breaks for
  most of the world. The user's ``push_timezone`` is used when they set one,
  otherwise the fallback is UTC (same rule as :mod:`bot.services.push_delivery`).
* **Freezes.** Tarot is inherently occasional, so a single missed day must not
  destroy a long streak. One skipped day is covered by a freeze instead of
  breaking the run — the same mechanic popular habit trackers use. Freezes are
  earned at streak milestones, never bought, and are capped.

The arithmetic lives in pure functions (:func:`advance`, :func:`week_grid`) so it
can be reasoned about and tested without a database. Persistence is confined to
:func:`record_ritual_day`.
"""
from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select

from ..db.database import get_session
from ..db.models import RitualDay, User

logger = logging.getLogger(__name__)

# A freeze is earned every N consecutive days and the bank is capped, so a long
# streak cannot be hoarded into an unbreakable shield.
FREEZE_EVERY = 7
FREEZE_CAP = 3
# Days shown in the activity heatmap, in whole weeks.
HEATMAP_WEEKS = 18
FALLBACK_TIMEZONE = "UTC"


def resolve_zone(timezone_name: str | None) -> ZoneInfo:
    """Return a usable zone, falling back to UTC for unknown or unset names."""
    if not timezone_name:
        return ZoneInfo(FALLBACK_TIMEZONE)
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(FALLBACK_TIMEZONE)


def local_day(moment: datetime | None = None, timezone_name: str | None = None) -> date:
    """Return the user's local calendar day for an instant."""
    moment = moment or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(resolve_zone(timezone_name)).date()


@dataclass(frozen=True)
class StreakState:
    """Immutable streak snapshot. ``last_day`` is the user's local YYYY-MM-DD."""

    current: int = 0
    longest: int = 0
    last_day: date | None = None
    freezes: int = 0

    @property
    def active_today(self) -> bool:
        return self.last_day is not None and self.current > 0 and self._gap_days == 0

    @property
    def _gap_days(self) -> int:
        if self.last_day is None:
            return -1
        return (local_day() - self.last_day).days


def state_from_user(user: User) -> StreakState:
    """Read the persisted streak columns into a snapshot."""
    last_day: date | None = None
    if user.last_ritual_date:
        try:
            last_day = date.fromisoformat(user.last_ritual_date)
        except ValueError:
            last_day = None
    return StreakState(
        current=user.streak_current or 0,
        longest=user.streak_longest or 0,
        last_day=last_day,
        freezes=user.streak_freezes or 0,
    )


def advance(state: StreakState, today: date) -> StreakState:
    """Return the streak after the user shows up on ``today``.

    Idempotent within a day: showing up twice cannot inflate the counter. A
    future ``last_day`` (clock skew, or a user who moved west) is left untouched
    rather than silently rewound.
    """
    if state.last_day is not None and today < state.last_day:
        return state

    gap = None if state.last_day is None else (today - state.last_day).days
    if gap == 0:
        return state

    if gap == 1 or gap == 2 and state.freezes > 0:
        current = state.current + 1
        freezes = state.freezes
        if gap == 2:
            # The single missed day is covered, the freeze is spent.
            freezes -= 1
    else:
        # Either the first ever visit, or a gap a freeze cannot cover.
        current = 1
        freezes = state.freezes

    longest = max(state.longest, current)
    if current and current % FREEZE_EVERY == 0 and freezes < FREEZE_CAP:
        freezes += 1
    return replace(state, current=current, longest=longest, last_day=today, freezes=freezes)


def streak_broken(state: StreakState, today: date) -> bool:
    """True when the streak will be lost unless the user returns today.

    Used to render the gentle "your streak is waiting" nudge: a one-day gap is
    still recoverable with a freeze, so it must not read as a loss.
    """
    if state.last_day is None or state.current == 0:
        return False
    gap = (today - state.last_day).days
    return gap == 1 or (gap == 2 and state.freezes == 0)


def day_word(lang: str, count: int) -> str:
    """Localised "day" word for a count. Russian needs three plural forms."""
    if lang != "ru":
        return "day" if count == 1 else "days"
    if count % 10 == 1 and count % 100 != 11:
        return "день"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "дня"
    return "дней"


def streak_line(lang: str, state: StreakState, *, today: date | None = None) -> str:
    """Return the one-line streak status shown under the menu and a reading.

    Reads as encouragement rather than a debt: a waiting streak is invited back,
    a finished one is simply acknowledged.
    """
    from ..i18n import t

    today = today or local_day()
    if state.current <= 0:
        return t(lang, "streak_none")
    if streak_broken(state, today):
        return t(lang, "streak_at_risk")
    if state.last_day is not None and (today - state.last_day).days == 0:
        return t(lang, "streak_active", n=state.current, word=day_word(lang, state.current))
    return t(lang, "streak_broken_today")


def week_grid(today: date, weeks: int = HEATMAP_WEEKS, firstweekday: int = calendar.MONDAY) -> list[list[date]]:
    """Return a ``weeks`` x 7 grid of dates laid out as columns of weeks.

    The last column is the week containing ``today``; the grid is padded with the
    preceding days of that week so every column holds exactly seven days. This is
    the familiar contribution-graph layout, used here to render the user's own
    ritual history.
    """
    last_weekday = (firstweekday - 1) % 7
    days_to_week_end = (last_weekday - today.weekday()) % 7
    last_day = today + timedelta(days=days_to_week_end)
    return [
        [last_day - timedelta(days=row, weeks=column) for column in reversed(range(weeks))]
        for row in reversed(range(7))
    ]


def month_labels(today: date, weeks: int = HEATMAP_WEEKS, firstweekday: int = calendar.MONDAY) -> list[str]:
    """Month captions aligned to :func:`week_grid` columns.

    A caption is emitted wherever the month changes, and the year is shown
    instead when the year rolls over inside the visible window. The reference
    habit tracker this layout comes from only ever assigned ``year`` inside its
    month-change branch, which printed a stray year on the second column; the
    state is tracked as one ``(year, month)`` key here to avoid that.
    """
    labels: list[str] = []
    previous: tuple[int, int] | None = None
    for column in week_grid(today, weeks, firstweekday)[0]:
        current = (column.year, column.month)
        if current == previous:
            labels.append("")
        elif previous is not None and current[0] != previous[0]:
            labels.append(str(current[0]))
        else:
            labels.append(calendar.month_abbr[current[1]])
        previous = current
    return labels


async def record_ritual_day(
    session,
    *,
    user_id: int,
    kind: str,
    moment: datetime | None = None,
    timezone_name: str | None = None,
) -> StreakState:
    """Register one ritual action and return the resulting streak.

    Safe to call for every completed action: repeated calls on the same local day
    are idempotent for the counters and only bump the per-day activity row.
    """
    user = await session.get(User, user_id)
    if user is None:
        raise ValueError("user_not_found")

    day = local_day(moment, timezone_name or user.push_timezone)
    state = advance(state_from_user(user), day)
    user.streak_current = state.current
    user.streak_longest = state.longest
    user.streak_freezes = state.freezes
    user.last_ritual_date = day.isoformat()

    row = await session.scalar(
        select(RitualDay).where(RitualDay.user_id == user_id, RitualDay.day == day.isoformat())
    )
    if row is None:
        session.add(RitualDay(user_id=user_id, day=day.isoformat(), actions=1, first_kind=kind))
    else:
        row.actions += 1
    return state


async def track_ritual(user_id: int, kind: str) -> StreakState | None:
    """Best-effort streak update for a completed user action.

    Streak bookkeeping is a retention signal, never a precondition for showing a
    result, so any failure is logged and swallowed. Returns ``None`` when the
    update could not be persisted.
    """
    try:
        async with get_session() as session:
            state = await record_ritual_day(session, user_id=user_id, kind=kind)
            await session.commit()
            return state
    except Exception as exc:  # noqa: BLE001
        logger.warning("ritual tracking failed for user %s: %s", user_id, exc)
        return None


async def ritual_days(session, *, user_id: int, since: date) -> dict[str, int]:
    """Return ``{iso_day: actions}`` for the heatmap window."""
    rows = (
        (
            await session.execute(
                select(RitualDay.day, RitualDay.actions).where(
                    RitualDay.user_id == user_id, RitualDay.day >= since.isoformat()
                )
            )
        )
        .tuples()
        .all()
    )
    return {day: actions for day, actions in rows}
