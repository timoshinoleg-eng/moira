"""Ritual streaks: arithmetic, freezes, local days and the activity heatmap.

The streak is the return loop, so the rules are pinned here rather than left to
the handler layer: a day may only count once, one missed day is covered by a
freeze instead of breaking a long run, and the count follows the user's local
calendar day rather than UTC.
"""
from __future__ import annotations

import asyncio
import calendar
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from bot.db.models import RitualDay, User
from bot.services.streaks import (
    FREEZE_CAP,
    FREEZE_EVERY,
    StreakState,
    advance,
    day_word,
    local_day,
    month_labels,
    resolve_zone,
    state_from_user,
    streak_broken,
    streak_line,
    week_grid,
)

DAY = timedelta(days=1)


def test_first_visit_starts_a_streak_of_one() -> None:
    state = advance(StreakState(), date(2026, 9, 27))
    assert state.current == 1
    assert state.longest == 1
    assert state.last_day == date(2026, 9, 27)


def test_consecutive_days_extend_the_streak() -> None:
    state = StreakState()
    for offset in range(5):
        state = advance(state, date(2026, 9, 27) + offset * DAY)
    assert state.current == 5
    assert state.longest == 5


def test_a_day_can_only_count_once() -> None:
    """Two readings in one day must not read as a two-day streak."""
    today = date(2026, 9, 27)
    once = advance(StreakState(current=4, longest=9, last_day=today - DAY), today)
    twice = advance(once, today)
    assert once.current == 5
    assert twice == once


def test_a_two_day_gap_breaks_the_streak() -> None:
    state = StreakState(current=9, longest=9, last_day=date(2026, 9, 20))
    after = advance(state, date(2026, 9, 23))
    assert after.current == 1
    assert after.longest == 9  # the record is never lost


def test_a_freeze_covers_exactly_one_missed_day() -> None:
    state = StreakState(current=4, longest=4, last_day=date(2026, 9, 20), freezes=1)
    after = advance(state, date(2026, 9, 22))
    assert after.current == 5
    assert after.freezes == 0
    assert after.last_day == date(2026, 9, 22)


def test_a_second_missed_day_breaks_the_streak() -> None:
    state = StreakState(current=4, longest=4, last_day=date(2026, 9, 20), freezes=1)
    after = advance(state, date(2026, 9, 23))
    assert after.current == 1
    assert after.freezes == 1, "a freeze is not spent on a gap it cannot cover"


def test_freezes_are_earned_at_milestones_and_capped() -> None:
    state = StreakState()
    day = date(2026, 9, 1)
    for _ in range(FREEZE_EVERY * 8):
        state = advance(state, day)
        day += DAY
    assert state.current == FREEZE_EVERY * 8
    assert state.freezes == FREEZE_CAP


def test_no_freeze_is_awarded_for_a_broken_restart() -> None:
    state = advance(StreakState(current=6, longest=6, last_day=date(2026, 1, 1)), date(2026, 3, 1))
    assert state.current == 1
    assert state.freezes == 0


def test_a_future_last_day_is_not_rewound() -> None:
    """Clock skew or moving west must not silently drop a streak."""
    state = StreakState(current=6, longest=6, last_day=date(2026, 9, 27))
    assert advance(state, date(2026, 9, 20)) is state


def test_streak_at_risk_distinguishes_a_recoverable_gap() -> None:
    today = date(2026, 9, 27)
    with_freeze = StreakState(current=3, longest=3, last_day=today - 2 * DAY, freezes=1)
    without = StreakState(current=3, longest=3, last_day=today - 2 * DAY, freezes=0)
    assert streak_broken(with_freeze, today) is False
    assert streak_broken(without, today) is True
    assert streak_broken(StreakState(current=3, longest=3, last_day=today - DAY), today) is True
    assert streak_broken(StreakState(), today) is False


def test_state_from_user_tolerates_a_corrupt_date() -> None:
    user = User(id=1, language="ru", streak_current=3, streak_longest=4, last_ritual_date="nope")
    state = state_from_user(user)
    assert state.last_day is None
    assert state.current == 3
    assert state.longest == 4


def test_local_day_follows_the_users_timezone() -> None:
    # 22:30 UTC is already the next day in Moscow and still the same day in New York.
    moment = datetime(2026, 9, 27, 22, 30, tzinfo=UTC)
    assert local_day(moment, "Europe/Moscow") == date(2026, 9, 28)
    assert local_day(moment, "America/New_York") == date(2026, 9, 27)
    assert local_day(moment, None) == date(2026, 9, 27)


def test_unknown_timezone_falls_back_to_utc() -> None:
    assert resolve_zone("Not/AZone") .key == "UTC"
    assert resolve_zone(None).key == "UTC"
    assert local_day(datetime(2026, 9, 27, 23, 0, tzinfo=UTC), "Bad/Zone") == date(2026, 9, 27)


def test_naive_moment_is_treated_as_utc() -> None:
    assert local_day(datetime(2026, 9, 27, 10, 0)) == date(2026, 9, 27)


def test_week_grid_is_seven_days_by_n_weeks_ending_this_week() -> None:
    """Rows are weekdays, columns are weeks, the last column is the current week."""
    today = date(2026, 9, 27)  # a Sunday
    grid = week_grid(today, weeks=4)
    assert len(grid) == 7
    assert all(len(column) == 4 for column in grid)
    # Row 6 is Sunday and closes the current week on today itself.
    assert grid[6][-1] == today
    assert list(grid[6]) == [today - 7 * i * DAY for i in (3, 2, 1, 0)]
    # Row 0 is the Monday of the same week.
    assert grid[0][-1] == today - 6 * DAY
    assert grid[0][-1].weekday() == calendar.MONDAY


def test_week_grid_start_day_can_be_monday_or_sunday() -> None:
    today = date(2026, 9, 27)
    monday_first = week_grid(today, weeks=2, firstweekday=calendar.MONDAY)
    sunday_first = week_grid(today, weeks=2, firstweekday=calendar.SUNDAY)
    assert monday_first[0][0].weekday() == calendar.MONDAY
    assert sunday_first[0][0].weekday() == calendar.SUNDAY
    # Sunday-first windows close on the Saturday of the current week.
    assert sunday_first[6][-1].weekday() == calendar.SATURDAY


def test_month_labels_align_with_grid_columns() -> None:
    today = date(2026, 9, 27)
    labels = month_labels(today, weeks=6)
    assert len(labels) == 6
    # One caption per month change, and no stray year inside a single year.
    assert [label for label in labels if label] == ["Aug", "Sep"]


def test_month_labels_show_the_year_only_when_it_rolls_over() -> None:
    labels = month_labels(date(2026, 1, 5), weeks=30)
    assert [label for label in labels if label.isdigit()] == ["2026"]


@pytest.mark.parametrize(
    ("count", "expected"),
    [(1, "день"), (2, "дня"), (5, "дней"), (11, "дней"), (21, "день"), (22, "дня"), (25, "дней")],
)
def test_russian_plural_forms(count: int, expected: str) -> None:
    assert day_word("ru", count) == expected


def test_english_day_word() -> None:
    assert day_word("en", 1) == "day"
    assert day_word("en", 3) == "days"


def test_streak_line_is_localised_and_encouraging() -> None:
    from bot.i18n import t

    today = date(2026, 9, 27)
    fresh = streak_line("ru", StreakState(), today=today)
    assert fresh == t("ru", "streak_none")

    active = streak_line("ru", StreakState(current=7, longest=7, last_day=today), today=today)
    assert "7" in active and "дней" in active

    waiting = streak_line(
        "ru", StreakState(current=7, longest=7, last_day=today - DAY), today=today
    )
    assert waiting == t("ru", "streak_at_risk")

    english = streak_line("en", StreakState(current=1, longest=1, last_day=today), today=today)
    assert english == t("en", "streak_active", n=1, word="day")


def test_record_ritual_day_persists_and_is_idempotent(tmp_path) -> None:
    from bot.db.database import close_db, get_session, init_db
    from bot.services.streaks import record_ritual_day

    async def run() -> None:
        await init_db(str(tmp_path / "streaks.db"))
        moment = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
        async with get_session() as session:
            session.add(User(id=7, language="ru", push_timezone="Europe/Moscow"))
            await session.commit()

        async with get_session() as session:
            first = await record_ritual_day(session, user_id=7, kind="reading", moment=moment)
            await session.commit()
        assert first.current == 1

        async with get_session() as session:
            again = await record_ritual_day(session, user_id=7, kind="altar", moment=moment)
            await session.commit()
        assert again.current == 1, "a second action on the same local day is not a new day"

        async with get_session() as session:
            rows = (await session.execute(select(RitualDay))).scalars().all()
            user = await session.get(User, 7)
        assert len(rows) == 1
        assert rows[0].actions == 2
        assert rows[0].first_kind == "reading"
        assert user.streak_current == 1
        assert user.last_ritual_date == "2026-09-27"
        await close_db()

    asyncio.run(run())


def test_record_ritual_day_uses_the_local_day(tmp_path) -> None:
    from bot.db.database import close_db, get_session, init_db
    from bot.services.streaks import record_ritual_day

    async def run() -> None:
        await init_db(str(tmp_path / "streaks-tz.db"))
        # 22:30 UTC on the 27th is the 28th in Moscow.
        moment = datetime(2026, 9, 27, 22, 30, tzinfo=UTC)
        async with get_session() as session:
            session.add(User(id=8, language="ru", push_timezone="Europe/Moscow"))
            await session.commit()
        async with get_session() as session:
            await record_ritual_day(session, user_id=8, kind="reading", moment=moment)
            await session.commit()
        async with get_session() as session:
            user = await session.get(User, 8)
        assert user.last_ritual_date == "2026-09-28"
        await close_db()

    asyncio.run(run())


def test_track_ritual_swallows_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """A streak write must never take down the flow that triggered it."""
    from bot.services import streaks

    @asynccontextmanager
    async def boom():
        raise RuntimeError("database is gone")
        yield  # pragma: no cover - unreachable, keeps this an async generator

    monkeypatch.setattr(streaks, "get_session", boom)
    assert asyncio.run(streaks.track_ritual(1, "reading")) is None


def test_streaks_migration_downgrade_cycle(tmp_path) -> None:
    """The streak migration must roll back cleanly and leave no partial state."""
    import os
    import sqlite3
    import subprocess
    import sys

    db_path = str(tmp_path / "moira-streak-cycle.db")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["DB_PATH"] = db_path

    def alembic(*args: str):
        return subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=root, env=env, capture_output=True, text=True,
        )

    assert alembic("upgrade", "head").returncode == 0
    assert alembic("check").returncode == 0

    # Target this revision explicitly so later migrations do not silently move it.
    assert alembic("downgrade", "0010_reading_notes").returncode == 0
    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    assert "ritual_days" not in tables
    assert not {"streak_current", "streak_longest", "streak_freezes", "last_ritual_date"} & columns

    assert alembic("upgrade", "head").returncode == 0
    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    assert "ritual_days" in tables
    assert {"streak_current", "last_ritual_date"} <= columns
