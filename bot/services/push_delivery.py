"""Domain services for timezone-aware, idempotent push delivery.

This module owns scheduling state only. It deliberately never renders a message
or calls Telegram; those side effects belong to the M-09 delivery worker.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import PushDelivery, User

DAILY_ALTAR = "daily_altar"
WEEKLY_MIRROR = "weekly_mirror"
PLANNED = "planned"
CLAIMED = "claimed"
SENT = "sent"
FAILED = "failed"
CANCELLED = "cancelled"
RETRYABLE_STATUSES = (PLANNED, FAILED)


class PushPreferenceError(ValueError):
    """Raised when a timezone or local wall-clock time is invalid."""


def utcnow() -> datetime:
    return datetime.now(UTC)


def validate_timezone(timezone_name: str) -> ZoneInfo:
    """Return an IANA timezone or raise a stable user-input error."""
    value = (timezone_name or "").strip()
    if not value or len(value) > 64:
        raise PushPreferenceError("invalid_timezone")
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise PushPreferenceError("invalid_timezone") from exc


def parse_local_time(value: str) -> time:
    """Parse strict 24-hour HH:MM without accepting locale-dependent strings."""
    raw = (value or "").strip()
    if len(raw) != 5 or raw[2] != ":" or not (raw[:2] + raw[3:]).isdigit():
        raise PushPreferenceError("invalid_local_time")
    hour, minute = int(raw[:2]), int(raw[3:])
    if hour > 23 or minute > 59:
        raise PushPreferenceError("invalid_local_time")
    return time(hour=hour, minute=minute)


def _roundtrip_is_valid(naive: datetime, zone: ZoneInfo, fold: int) -> bool:
    candidate = naive.replace(tzinfo=zone, fold=fold)
    return candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None) == naive


def resolve_local_wall_time(local_day: date, local_time: time, timezone_name: str) -> datetime:
    """Resolve an IANA wall time using one deterministic DST policy.

    An ambiguous fall-back time uses the first occurrence (`fold=0`). A spring
    gap moves to the first valid minute after the requested wall time. This
    guarantees one stable scheduled instant for a chosen local date.
    """
    zone = validate_timezone(timezone_name)
    naive = datetime.combine(local_day, local_time)
    for minute_offset in range(0, 24 * 60 + 1):
        candidate = naive + timedelta(minutes=minute_offset)
        if _roundtrip_is_valid(candidate, zone, fold=0):
            return candidate.replace(tzinfo=zone, fold=0)
    raise PushPreferenceError("unresolvable_local_time")


def next_push_at_utc(
    *,
    now: datetime,
    timezone_name: str,
    local_time_value: str,
) -> datetime:
    """Return the first configured local wall-clock instant strictly after now."""
    if now.tzinfo is None:
        raise PushPreferenceError("naive_now")
    zone = validate_timezone(timezone_name)
    local_time = parse_local_time(local_time_value)
    local_now = now.astimezone(zone)
    candidate = resolve_local_wall_time(local_now.date(), local_time, timezone_name)
    if candidate.astimezone(UTC) <= now.astimezone(UTC):
        candidate = resolve_local_wall_time(local_now.date() + timedelta(days=1), local_time, timezone_name)
    return candidate.astimezone(UTC)


def local_period_for(*, scheduled_at: datetime, timezone_name: str, kind: str) -> str:
    """Return a stable local day/week period used in the delivery uniqueness key."""
    if scheduled_at.tzinfo is None:
        raise PushPreferenceError("naive_scheduled_at")
    local_dt = scheduled_at.astimezone(validate_timezone(timezone_name))
    if kind == DAILY_ALTAR:
        return local_dt.date().isoformat()
    if kind == WEEKLY_MIRROR:
        year, week, _weekday = local_dt.isocalendar()
        return f"{year:04d}-W{week:02d}"
    raise PushPreferenceError("invalid_push_kind")


async def configure_push_preference(
    session: AsyncSession,
    *,
    user_id: int,
    enabled: bool,
    timezone_name: str | None = None,
    local_time_value: str | None = None,
    now: datetime | None = None,
) -> User:
    """Persist an explicit V2 preference without scheduling historical delivery rows."""
    user = await session.get(User, user_id)
    if user is None:
        raise PushPreferenceError("user_not_found")
    if not enabled:
        user.push_enabled = False
        user.next_push_at_utc = None
        return user
    if timezone_name is None or local_time_value is None:
        raise PushPreferenceError("missing_push_preference")

    moment = now or utcnow()
    next_at = next_push_at_utc(
        now=moment,
        timezone_name=timezone_name,
        local_time_value=local_time_value,
    )
    user.push_enabled = True
    user.push_timezone = timezone_name
    user.push_local_time = local_time_value
    user.next_push_at_utc = next_at
    return user


async def plan_delivery(
    session: AsyncSession,
    *,
    user_id: int,
    kind: str,
    local_period: str,
    scheduled_at: datetime,
) -> bool:
    """Create a delivery row once; return True only for the transaction winner."""
    if scheduled_at.tzinfo is None:
        raise PushPreferenceError("naive_scheduled_at")
    statement = (
        sqlite_insert(PushDelivery)
        .values(
            user_id=user_id,
            kind=kind,
            local_period=local_period,
            scheduled_at=scheduled_at.astimezone(UTC),
            status=PLANNED,
            attempt_count=0,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["user_id", "kind", "local_period"])
    )
    result = await session.execute(statement)
    return bool(result.rowcount)


async def claim_delivery(
    session: AsyncSession,
    *,
    delivery_id: int,
    worker_id: str,
    now: datetime | None = None,
    lease_seconds: int = 300,
) -> bool:
    """Atomically claim a due/retryable delivery and bound a crash-recovery lease."""
    if not worker_id or len(worker_id) > 64:
        raise PushPreferenceError("invalid_worker_id")
    moment = now or utcnow()
    lease_until = moment + timedelta(seconds=lease_seconds)
    statement = (
        update(PushDelivery)
        .execution_options(synchronize_session=False)
        .where(
            PushDelivery.id == delivery_id,
            PushDelivery.status.in_(RETRYABLE_STATUSES),
            PushDelivery.scheduled_at <= moment,
        )
        .values(
            status=CLAIMED,
            claimed_at=moment,
            lease_until=lease_until,
            attempt_count=PushDelivery.attempt_count + 1,
            last_error_code=None,
            updated_at=moment,
        )
    )
    result = await session.execute(statement)
    return bool(result.rowcount)


async def mark_delivery_sent(
    session: AsyncSession,
    *,
    delivery_id: int,
    now: datetime | None = None,
) -> bool:
    """Mark only a claimed row as sent after a successful external API call."""
    moment = now or utcnow()
    statement = (
        update(PushDelivery)
        .execution_options(synchronize_session=False)
        .where(PushDelivery.id == delivery_id, PushDelivery.status == CLAIMED)
        .values(status=SENT, sent_at=moment, lease_until=None, updated_at=moment)
    )
    result = await session.execute(statement)
    return bool(result.rowcount)


async def mark_delivery_failed(
    session: AsyncSession,
    *,
    delivery_id: int,
    error_code: str,
    now: datetime | None = None,
    terminal: bool = False,
) -> bool:
    """Record a bounded safe error code; caller decides retry policy in M-09."""
    code = (error_code or "unknown")[:32]
    moment = now or utcnow()
    statement = (
        update(PushDelivery)
        .execution_options(synchronize_session=False)
        .where(PushDelivery.id == delivery_id, PushDelivery.status == CLAIMED)
        .values(
            status=CANCELLED if terminal else FAILED,
            lease_until=None,
            last_error_code=code,
            updated_at=moment,
        )
    )
    result = await session.execute(statement)
    return bool(result.rowcount)


async def recover_expired_claims(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Return abandoned claims to retryable state without creating new delivery rows."""
    moment = now or utcnow()
    statement = (
        update(PushDelivery)
        .execution_options(synchronize_session=False)
        .where(
            PushDelivery.status == CLAIMED,
            PushDelivery.lease_until.is_not(None),
            PushDelivery.lease_until < moment,
        )
        .values(
            status=FAILED,
            lease_until=None,
            last_error_code="lease_expired",
            updated_at=moment,
        )
    )
    result = await session.execute(statement)
    return int(result.rowcount or 0)
