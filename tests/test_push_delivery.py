"""Contract tests for M-07 timezone-aware push delivery foundation."""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.db.database import close_db, get_session, init_db
from bot.db.models import PushDelivery, User
from bot.services.push_delivery import (
    CLAIMED,
    DAILY_ALTAR,
    FAILED,
    PLANNED,
    SENT,
    PushPreferenceError,
    claim_delivery,
    configure_push_preference,
    local_period_for,
    mark_delivery_failed,
    mark_delivery_sent,
    next_push_at_utc,
    parse_local_time,
    plan_delivery,
    recover_expired_claims,
    resolve_local_wall_time,
    validate_timezone,
)


def test_timezone_and_time_validation_are_strict() -> None:
    assert validate_timezone("Europe/Moscow").key == "Europe/Moscow"
    assert parse_local_time("09:05") == time(9, 5)
    for value in ("", "UTC+3", "Not/AZone"):
        with pytest.raises(PushPreferenceError, match="invalid_timezone"):
            validate_timezone(value)
    for value in ("9:05", "24:00", "12:60", "noon"):
        with pytest.raises(PushPreferenceError, match="invalid_local_time"):
            parse_local_time(value)


def test_dst_policy_moves_gap_forward_and_uses_first_ambiguous_occurrence() -> None:
    gap = resolve_local_wall_time(date(2026, 3, 8), time(2, 30), "America/New_York")
    assert gap.hour == 3 and gap.minute == 0
    assert gap.astimezone(UTC) == datetime(2026, 3, 8, 7, 0, tzinfo=UTC)

    fold = resolve_local_wall_time(date(2026, 11, 1), time(1, 30), "America/New_York")
    assert fold.fold == 0
    assert fold.astimezone(UTC) == datetime(2026, 11, 1, 5, 30, tzinfo=UTC)


def test_next_push_and_local_period_use_user_timezone() -> None:
    now = datetime(2026, 1, 5, 23, 30, tzinfo=UTC)
    next_at = next_push_at_utc(
        now=now,
        timezone_name="Europe/Moscow",
        local_time_value="09:00",
    )
    assert next_at == datetime(2026, 1, 6, 6, 0, tzinfo=UTC)
    assert local_period_for(
        scheduled_at=next_at, timezone_name="Europe/Moscow", kind=DAILY_ALTAR
    ) == "2026-01-06"


def test_preference_and_delivery_state_machine_is_idempotent(tmp_path) -> None:
    async def run() -> None:
        await init_db(str(tmp_path / "push-delivery.db"))
        now = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
        async with get_session() as session:
            session.add(User(id=1001, language="ru", daily_push=True))
            await session.commit()

        async with get_session() as session:
            user = await configure_push_preference(
                session,
                user_id=1001,
                enabled=True,
                timezone_name="Europe/Moscow",
                local_time_value="12:30",
                now=now,
            )
            assert user.push_enabled is True
            assert user.push_timezone == "Europe/Moscow"
            assert user.push_local_time == "12:30"
            assert user.next_push_at_utc == datetime(2026, 1, 5, 9, 30, tzinfo=UTC)
            await session.commit()

        scheduled_at = datetime(2026, 1, 5, 9, 30, tzinfo=UTC)
        async with get_session() as session:
            first = await plan_delivery(
                session,
                user_id=1001,
                kind=DAILY_ALTAR,
                local_period="2026-01-05",
                scheduled_at=scheduled_at,
            )
            duplicate = await plan_delivery(
                session,
                user_id=1001,
                kind=DAILY_ALTAR,
                local_period="2026-01-05",
                scheduled_at=scheduled_at,
            )
            await session.commit()
            assert first is True
            assert duplicate is False

        async with get_session() as session:
            delivery = (await session.execute(select(PushDelivery))).scalar_one()
            assert delivery.status == PLANNED
            assert await claim_delivery(
                session, delivery_id=delivery.id, worker_id="test-worker", now=scheduled_at
            ) is True
            assert await claim_delivery(
                session, delivery_id=delivery.id, worker_id="test-worker", now=scheduled_at
            ) is False
            await session.commit()

        async with get_session() as session:
            delivery = (await session.execute(select(PushDelivery))).scalar_one()
            assert delivery.status == CLAIMED
            assert delivery.attempt_count == 1
            assert await mark_delivery_sent(session, delivery_id=delivery.id, now=scheduled_at) is True
            assert await mark_delivery_sent(session, delivery_id=delivery.id, now=scheduled_at) is False
            await session.commit()

        async with get_session() as session:
            delivery = (await session.execute(select(PushDelivery))).scalar_one()
            assert delivery.status == SENT
            assert delivery.sent_at is not None

        await close_db()

    asyncio.run(run())


def test_expired_claim_is_recoverable_and_terminal_failure_is_not(tmp_path) -> None:
    async def run() -> None:
        await init_db(str(tmp_path / "push-recovery.db"))
        now = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
        async with get_session() as session:
            session.add(User(id=1002, language="en"))
            await session.commit()
            await plan_delivery(
                session,
                user_id=1002,
                kind=DAILY_ALTAR,
                local_period="2026-01-05",
                scheduled_at=now,
            )
            await session.commit()

        async with get_session() as session:
            delivery = (await session.execute(select(PushDelivery))).scalar_one()
            assert await claim_delivery(
                session, delivery_id=delivery.id, worker_id="worker", now=now, lease_seconds=60
            ) is True
            await session.commit()

        async with get_session() as session:
            recovered = await recover_expired_claims(session, now=now + timedelta(seconds=61))
            await session.commit()
            assert recovered == 1

        async with get_session() as session:
            delivery = (await session.execute(select(PushDelivery))).scalar_one()
            assert delivery.status == FAILED
            assert delivery.last_error_code == "lease_expired"
            assert await claim_delivery(
                session, delivery_id=delivery.id, worker_id="worker", now=now + timedelta(seconds=61)
            ) is True
            assert await mark_delivery_failed(
                session,
                delivery_id=delivery.id,
                error_code="chat_not_found",
                terminal=True,
                now=now + timedelta(seconds=62),
            ) is True
            await session.commit()

        async with get_session() as session:
            delivery = (await session.execute(select(PushDelivery))).scalar_one()
            assert delivery.status == "cancelled"
            assert await claim_delivery(
                session, delivery_id=delivery.id, worker_id="worker", now=now + timedelta(seconds=63)
            ) is False

        await close_db()

    asyncio.run(run())
