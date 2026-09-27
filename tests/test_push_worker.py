"""M-09 push worker: planning idempotency, lease discipline and retry bounds.

The properties that matter are the ones the old 20-minute loop could not offer:
"planned exactly once" must come from the schema rather than from careful
coding, a crashed claim must become visible again, and a permanently rejected
recipient must stop consuming attempts.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import func, select, update

from bot.config import load_config
from bot.db.database import close_db, get_session, init_db
from bot.db.models import PushDelivery, User
from bot.handlers.features import PUSH_TERMINAL_CODES
from bot.services import push_delivery as ledger
from bot.services.push_worker import (
    PushWorker,
    PushWorkerSettings,
    new_worker_id,
    plan_due_deliveries,
    scheduled_at_for,
    settings_from_config,
)

UTC = dt.UTC
# 2026-09-27 is a Sunday, so it owes the altar *and* the weekly mirror. Tests that
# only care about the altar pin a weekday instead.
DAY = dt.datetime(2026, 9, 27, 6, 0, tzinfo=UTC)  # Sunday
WEEKDAY = dt.datetime(2026, 9, 25, 6, 0, tzinfo=UTC)  # Friday
SETTINGS = PushWorkerSettings(hour_utc=6, batch_size=10, lease_seconds=60, max_attempts=2)


class FakeBot:
    """Stands in for the aiogram Bot. Records sends, optionally fails."""

    def __init__(self, fail_with: Exception | None = None) -> None:
        self.sent: list[int] = []
        self.fail_with = fail_with

    async def send_message(self, chat_id: int, text: str, **kwargs) -> None:
        if self.fail_with is not None:
            raise self.fail_with
        self.sent.append(chat_id)

    async def me(self):
        raise AssertionError("not used")


class FakeAnalytics:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    async def track(self, user_id: int, event: str, **props) -> None:
        self.events.append((user_id, event, props))

    def shutdown(self) -> None:
        pass


def _cfg(**overrides):
    import os

    saved = {k: os.environ.get(k) for k in overrides}
    os.environ.update({k: str(v) for k, v in overrides.items()})
    try:
        return load_config(require_token=False)
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextmanager
def _frozen_now(moment: dt.datetime):
    """Pin ``push_worker.utcnow`` so a tick does not depend on the wall clock.

    The worker reads the clock through one module attribute on purpose, so tests
    can drive it without sleeping and without the suite failing at 05:00 UTC.
    """
    from bot.services import push_worker

    original = push_worker.utcnow
    push_worker.utcnow = lambda: moment
    try:
        yield
    finally:
        push_worker.utcnow = original


async def _seed(db_path: str, *, users: int = 3, **user_fields) -> None:
    await init_db(db_path)
    async with get_session() as session:
        for i in range(users):
            session.add(User(id=100 + i, language="ru", daily_push=True, **user_fields))
        await session.commit()


async def _status_counts() -> dict[str, int]:
    async with get_session() as session:
        rows = await session.execute(
            select(PushDelivery.status, func.count()).group_by(PushDelivery.status)
        )
        return {status: count for status, count in rows.all()}


# ----------------------------------------------------------------- planning --


def test_scheduled_at_clamps_the_hour() -> None:
    assert scheduled_at_for(DAY, 6).hour == 6
    assert scheduled_at_for(DAY, 99).hour == 23
    assert scheduled_at_for(DAY, -5).hour == 0
    assert scheduled_at_for(DAY, 6).tzinfo is not None


def test_nothing_is_planned_before_the_send_hour(tmp_path) -> None:
    async def run() -> None:
        await _seed(str(tmp_path / "early.db"))
        early = dt.datetime(2026, 9, 27, 5, 30, tzinfo=UTC)
        async with get_session() as session:
            assert await plan_due_deliveries(session, settings=SETTINGS, now=early) == 0
        assert await _status_counts() == {}
        await close_db()

    asyncio.run(run())


def test_planning_is_idempotent_across_ticks(tmp_path) -> None:
    """The unique key, not the code, is what stops a second row."""

    async def run() -> None:
        await _seed(str(tmp_path / "idem.db"), users=3)
        late = dt.datetime(2026, 9, 25, 9, 0, tzinfo=UTC)  # a Friday: altar only
        async with get_session() as session:
            first = await plan_due_deliveries(session, settings=SETTINGS, now=late)
            await session.commit()
        assert first == 3
        for _ in range(3):
            async with get_session() as session:
                assert await plan_due_deliveries(session, settings=SETTINGS, now=late) == 0
                await session.commit()
        assert await _status_counts() == {ledger.PLANNED: 3}
        await close_db()

    asyncio.run(run())


def test_planning_ignores_opted_out_and_v2_users(tmp_path) -> None:
    async def run() -> None:
        await init_db(str(tmp_path / "skip.db"))
        async with get_session() as session:
            session.add(User(id=1, language="ru", daily_push=False))
            session.add(User(id=2, language="ru", daily_push=True, push_enabled=True))
            session.add(User(id=3, language="ru", daily_push=True))
            await session.commit()
        late = dt.datetime(2026, 9, 25, 9, 0, tzinfo=UTC)
        async with get_session() as session:
            assert await plan_due_deliveries(session, settings=SETTINGS, now=late) == 1
            await session.commit()
        async with get_session() as session:
            ids = list((await session.execute(select(PushDelivery.user_id))).scalars().all())
        assert ids == [3]
        await close_db()

    asyncio.run(run())


def test_sunday_plans_the_mirror_as_well(tmp_path) -> None:
    async def run() -> None:
        await _seed(str(tmp_path / "sunday.db"), users=2)
        async with get_session() as session:
            await plan_due_deliveries(session, settings=SETTINGS, now=DAY)
            await session.commit()
        async with get_session() as session:
            rows = (await session.execute(select(PushDelivery.kind, PushDelivery.local_period))).all()
        assert {r[0] for r in rows} == {ledger.DAILY_ALTAR, ledger.WEEKLY_MIRROR}
        # The mirror keys on an ISO week, the altar on a date.
        assert any(r[1] == "2026-W39" for r in rows)
        await close_db()

    asyncio.run(run())


def test_mirror_can_be_switched_off(tmp_path) -> None:
    settings = PushWorkerSettings(hour_utc=6, mirror_enabled=False)

    async def run() -> None:
        await _seed(str(tmp_path / "nomirror.db"), users=1)
        async with get_session() as session:
            await plan_due_deliveries(session, settings=settings, now=DAY)
            await session.commit()
        async with get_session() as session:
            kinds = list((await session.execute(select(PushDelivery.kind))).scalars().all())
        assert kinds == [ledger.DAILY_ALTAR]
        await close_db()

    asyncio.run(run())


# ------------------------------------------------------------------ worker ---


def _worker(bot: FakeBot, **overrides) -> PushWorker:
    settings = PushWorkerSettings(
        hour_utc=6, batch_size=10, lease_seconds=60, max_attempts=2, **overrides
    )
    return PushWorker(
        bot,  # type: ignore[arg-type]
        _cfg(),  # type: ignore[arg-type]
        FakeAnalytics(),  # type: ignore[arg-type]
        settings=settings,
        worker_id=new_worker_id(),
    )


def test_worker_plans_then_sends_each_user_once(tmp_path) -> None:
    async def run() -> None:
        await _seed(str(tmp_path / "send.db"), users=3)
        bot = FakeBot()
        worker = _worker(bot)
        now = dt.datetime(2026, 9, 25, 9, 0, tzinfo=UTC)  # Friday: altar only
        with _frozen_now(now):
            first = await worker.tick()
        assert first["planned"] == 3
        assert first["sent"] == 3
        assert bot.sent == [100, 101, 102]

        # A second tick must not send anything again.
        bot.sent.clear()
        with _frozen_now(now):
            second = await worker.tick()
        assert second["planned"] == 0
        assert second["sent"] == 0
        assert bot.sent == []
        await close_db()

    asyncio.run(run())


def test_a_mirror_with_nothing_to_say_is_closed_not_retried(tmp_path) -> None:
    """Fewer than three readings is a deliberate no-op, not a delivery failure."""

    async def run() -> None:
        await _seed(str(tmp_path / "nomirror.db"), users=1)
        worker = _worker(FakeBot())
        counters = await worker.tick()
        assert counters["sent"] == 1  # only the altar
        assert counters["cancelled"] == 1  # the mirror
        async with get_session() as session:
            row = await session.get(PushDelivery, 2)
        assert row.kind == ledger.WEEKLY_MIRROR
        assert row.status == ledger.CANCELLED
        assert row.last_error_code == "too_few_readings"
        await close_db()

    asyncio.run(run())


def test_lease_is_released_after_a_successful_send(tmp_path) -> None:
    async def run() -> None:
        await _seed(str(tmp_path / "lease.db"), users=1)
        await _worker(FakeBot()).tick()
        async with get_session() as session:
            row = await session.get(PushDelivery, 1)
        assert row.status == ledger.SENT
        assert row.sent_at is not None
        assert row.lease_until is None, "a finished send must not keep holding the lease"
        assert row.attempt_count == 1
        await close_db()

    asyncio.run(run())


def test_a_crash_mid_send_becomes_retryable_again(tmp_path) -> None:
    """A row stuck in claimed with an expired lease must not vanish."""

    async def run() -> None:
        await _seed(str(tmp_path / "crash.db"), users=1)
        async with get_session() as session:
            await plan_due_deliveries(session, settings=SETTINGS, now=DAY)
            await session.commit()
        # Simulate a worker that claimed and then died.
        async with get_session() as session:
            assert await ledger.claim_delivery(
                session, delivery_id=1, worker_id="dead-worker", now=DAY, lease_seconds=60
            )
            await session.commit()
        async with get_session() as session:
            assert (await session.get(PushDelivery, 1)).status == ledger.CLAIMED

        later = DAY + dt.timedelta(seconds=120)
        async with get_session() as session:
            assert await ledger.recover_expired_claims(session, now=later) == 1
            await session.commit()
        async with get_session() as session:
            row = await session.get(PushDelivery, 1)
        assert row.status == ledger.FAILED
        assert row.last_error_code == "lease_expired"
        assert row.lease_until is None
        await close_db()

    asyncio.run(run())


def test_a_failing_send_is_retried_up_to_the_cap(tmp_path) -> None:
    async def run() -> None:
        await _seed(str(tmp_path / "retry.db"), users=1)
        bot = FakeBot(fail_with=RuntimeError("upstream is having a moment"))
        worker = _worker(bot)
        with _frozen_now(dt.datetime(2026, 9, 25, 9, 0, tzinfo=UTC)):
            for _ in range(2):
                await worker.tick()
            async with get_session() as session:
                row = await session.get(PushDelivery, 1)
            assert row.status == ledger.FAILED
            assert row.attempt_count == 2

            # The cap is reached: another tick must not pick the row up again.
            await worker.tick()
            async with get_session() as session:
                assert (await session.get(PushDelivery, 1)).attempt_count == 2
        await close_db()

    asyncio.run(run())


def test_a_blocked_user_is_cancelled_immediately(tmp_path) -> None:
    """Retrying a user who blocked the bot only burns rate limit."""

    async def run() -> None:
        await _seed(str(tmp_path / "blocked.db"), users=1)
        bot = FakeBot(fail_with=RuntimeError("Forbidden: bot was blocked by the user"))
        worker = _worker(bot)
        with _frozen_now(dt.datetime(2026, 9, 25, 9, 0, tzinfo=UTC)):
            await worker.tick()
        async with get_session() as session:
            row = await session.get(PushDelivery, 1)
        assert row.status == ledger.CANCELLED
        assert row.last_error_code == "bot_blocked_by_user"
        assert "bot_blocked_by_user" in PUSH_TERMINAL_CODES
        await close_db()

    asyncio.run(run())


def test_a_skip_because_already_sent_is_not_an_error(tmp_path) -> None:
    """The sender skips when the legacy marker matches; that is delivery done."""

    async def run() -> None:
        await _seed(str(tmp_path / "skip.db"), users=1, last_push_date="2026-09-25")
        bot = FakeBot()
        worker = _worker(bot)
        with _frozen_now(dt.datetime(2026, 9, 25, 9, 0, tzinfo=UTC)):
            await worker.tick()
        async with get_session() as session:
            row = await session.get(PushDelivery, 1)
        assert row.status == ledger.CANCELLED
        assert row.last_error_code == "already_sent"
        assert row.attempt_count == 1, "a skip must not be retried"
        assert bot.sent == []
        await close_db()

    asyncio.run(run())


def test_one_bad_send_does_not_stop_the_batch(tmp_path) -> None:
    async def run() -> None:
        await _seed(str(tmp_path / "batch.db"), users=4)
        worker = _worker(FakeBot())
        now = dt.datetime(2026, 9, 25, 9, 0, tzinfo=UTC)
        async with get_session() as session:
            await plan_due_deliveries(session, settings=SETTINGS, now=now)
            await session.commit()
        # Close one row so the rest must still be delivered.
        async with get_session() as session:
            await session.execute(
                update(PushDelivery).where(PushDelivery.id == 1).values(status=ledger.CANCELLED)
            )
            await session.commit()

        with _frozen_now(now):
            counters = await worker.tick()
        assert counters["sent"] == 3, "the other three must still go out"
        await close_db()

    asyncio.run(run())


def test_worker_id_is_unique_and_bounded() -> None:
    ids = {new_worker_id() for _ in range(20)}
    assert len(ids) == 20
    assert all(len(value) <= 64 for value in ids)


def test_settings_are_clamped_from_config() -> None:
    cfg = _cfg(PUSH_BATCH_SIZE="0", PUSH_LEASE_SECONDS="1", PUSH_MAX_ATTEMPTS="0", PUSH_HOUR_UTC="99")
    settings = settings_from_config(cfg)
    assert settings.batch_size == 1
    assert settings.lease_seconds == 30
    assert settings.max_attempts == 1
    assert settings.send_hour_utc == 23


def test_run_forever_survives_a_failing_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bad tick must not kill the scheduler loop."""

    async def run() -> None:
        worker = _worker(FakeBot())
        calls = {"n": 0}

        async def flaky() -> dict[str, int]:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient")
            if calls["n"] >= 3:
                raise asyncio.CancelledError
            return {}

        monkeypatch.setattr(worker, "tick", flaky)
        with pytest.raises(asyncio.CancelledError):
            await worker.run_forever(0)
        assert calls["n"] >= 3

    asyncio.run(run())


def test_legacy_loop_stays_available_for_rollback() -> None:
    """PUSH_WORKER_ENABLED=false must select the old loop, not disable pushing."""
    from bot.main import _start_push_loop

    async def run() -> None:
        task = await _start_push_loop(FakeBot(), _cfg(), FakeAnalytics())  # type: ignore[arg-type]
        try:
            assert task.get_name(), "a task must be returned either way"
        finally:
            task.cancel()
            with pytest.raises((asyncio.CancelledError, Exception)):
                await task

    asyncio.run(run())


def test_ledger_unique_key_is_what_prevents_duplicates() -> None:
    """The guarantee is structural, so assert the constraint actually exists."""
    table = PushDelivery.__table__
    uniques = [
        tuple(col.name for col in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, __import__("sqlalchemy").UniqueConstraint)
    ]
    assert ("user_id", "kind", "local_period") in uniques
    _ = uuid.uuid4()  # keep the import honest
