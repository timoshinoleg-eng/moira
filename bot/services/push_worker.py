"""M-09: the delivery worker for the push ledger.

``bot/services/push_delivery.py`` owns scheduling state and never talks to
Telegram. This module is the missing half: it plans what is due, claims it under
a lease, sends it, and records the outcome.

**Why a ledger at all.** The previous implementation was a ``while True`` loop
that woke every 20 minutes, selected every opted-in user whose ``last_push_date``
was not today, and sent in batches of 30 inside one long-lived session. That
shape has three failure modes worth naming: a single slow send stalls the whole
batch, a crash mid-batch loses the work with no record of what was already sent,
and "already sent" is tracked in a mutable column rather than as an invariant.
Here, the unique key on ``(user_id, kind, local_period)`` makes "planned once"
a property of the schema instead of a convention, and a lease bounds how long a
crashed claim can hide work.

**Scope.** This is the fixed-hour variant: everyone is addressed at the same UTC
hour (06:00 UTC is roughly 09:00 in Moscow, the existing behaviour). Per-user
local time is deliberately not implemented — the opt-in timezone UI does not
exist yet, and asking for a preferred send time at signup is friction that
should not be paid before someone has said they want it. ``local_period`` is
already computed per user through ``local_period_for``, so that change is
additive later.
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime

from aiogram import Bot
from sqlalchemy import select

from ..config import Config
from ..db.database import get_session
from ..db.models import PushDelivery, User
from ..handlers.features import (
    PUSH_SKIP_CODES,
    PUSH_TERMINAL_CODES,
    classify_push_error,
    send_daily_push,
    send_weekly_mirror,
)
from ..services.analytics import Analytics
from .push_delivery import (
    DAILY_ALTAR,
    RETRYABLE_STATUSES,
    WEEKLY_MIRROR,
    claim_delivery,
    local_period_for,
    mark_delivery_failed,
    mark_delivery_sent,
    plan_delivery,
    recover_expired_claims,
    utcnow,
)

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class PushWorkerSettings:
    """Tunables for the delivery worker. Sourced from :class:`Config`."""

    hour_utc: int = 6
    batch_size: int = 50
    lease_seconds: int = 300
    max_attempts: int = 3
    mirror_enabled: bool = True

    @property
    def send_hour_utc(self) -> int:
        return max(0, min(23, self.hour_utc))


def settings_from_config(cfg: Config) -> PushWorkerSettings:
    return PushWorkerSettings(
        hour_utc=cfg.push_hour_utc,
        batch_size=max(1, cfg.push_batch_size),
        lease_seconds=max(30, cfg.push_lease_seconds),
        max_attempts=max(1, cfg.push_max_attempts),
        mirror_enabled=cfg.push_mirror_enabled,
    )


def new_worker_id() -> str:
    """A stable-per-process id so a lease can be attributed in the ledger."""
    return f"{socket.gethostname()[:24]}-{os.getpid()}-{uuid.uuid4().hex[:8]}"[:64]


def scheduled_at_for(day: datetime, hour_utc: int) -> datetime:
    """The instant this day becomes due: ``hour_utc`` UTC, clamped to the day."""
    return day.replace(hour=max(0, min(23, hour_utc)), minute=0, second=0, microsecond=0)


async def _unplanned_user_ids(session, *, kind: str, period: str, limit: int) -> list[int]:
    """Users owing this kind for this period who have no row yet.

    The ``NOT EXISTS`` keeps planning proportional to *newly* owed work rather than
    to the size of the user table, so a tick on a large install does not insert
    one conflicting row per user every time it runs.
    """
    already_planned = (
        select(PushDelivery.id)
        .where(
            PushDelivery.user_id == User.id,
            PushDelivery.kind == kind,
            PushDelivery.local_period == period,
        )
        .exists()
    )
    statement = (
        select(User.id)
        .where(
            User.daily_push.is_(True),
            User.push_enabled.is_(False),
            already_planned.is_(False),
        )
        .limit(limit)
    )
    return list((await session.execute(statement)).scalars().all())


async def plan_due_deliveries(
    session, *, settings: PushWorkerSettings, now: datetime | None = None
) -> int:
    """Insert the rows that should go out now. Idempotent by unique key."""
    moment = now or utcnow()
    due = scheduled_at_for(moment, settings.send_hour_utc)
    if moment < due:
        # Not yet: planning early would queue a row the dispatcher would refuse
        # until it came due anyway, and would only add write amplification.
        return 0

    planned = 0
    for kind in _kinds_for(moment, settings):
        period = local_period_for(scheduled_at=due, timezone_name="UTC", kind=kind)
        user_ids = await _unplanned_user_ids(
            session, kind=kind, period=period, limit=settings.batch_size * 4
        )
        for user_id in user_ids:
            if await plan_delivery(
                session, user_id=user_id, kind=kind, local_period=period, scheduled_at=due
            ):
                planned += 1
        if user_ids:
            await session.commit()
    return planned


def _kinds_for(moment: datetime, settings: PushWorkerSettings) -> tuple[str, ...]:
    """Which delivery kinds are owing for this day."""
    kinds = [DAILY_ALTAR]
    if settings.mirror_enabled and moment.weekday() == 6:
        kinds.append(WEEKLY_MIRROR)
    return tuple(kinds)


async def _due_rows(session, *, settings: PushWorkerSettings, now: datetime) -> list[tuple[int, int, str]]:
    statement = (
        select(PushDelivery.id, PushDelivery.user_id, PushDelivery.kind)
        .where(
            PushDelivery.status.in_(RETRYABLE_STATUSES),
            PushDelivery.scheduled_at <= now,
            PushDelivery.attempt_count < settings.max_attempts,
        )
        .order_by(PushDelivery.scheduled_at, PushDelivery.id)
        .limit(settings.batch_size)
    )
    return [(row.id, row.user_id, row.kind) for row in (await session.execute(statement)).all()]


class PushWorker:
    """Plans, claims and sends push deliveries. Safe to call repeatedly."""
    def __init__(
        self,
        bot: Bot,
        cfg: Config,
        analytics: Analytics,
        *,
        settings: PushWorkerSettings | None = None,
        worker_id: str | None = None,
    ) -> None:
        self.bot = bot
        self.cfg = cfg
        self.analytics = analytics
        self.settings = settings or settings_from_config(cfg)
        self.worker_id = worker_id or new_worker_id()

    async def tick(self) -> dict[str, int]:
        """One planning + dispatch pass. Returns counters for logging."""
        now = utcnow()
        counters = {"planned": 0, "sent": 0, "failed": 0, "cancelled": 0, "recovered": 0}

        async with get_session() as session:
            counters["recovered"] = await recover_expired_claims(session, now=now)
            await session.commit()
            counters["planned"] = await plan_due_deliveries(session, settings=self.settings, now=now)

        async with get_session() as session:
            for delivery_id, user_id, kind in await _due_rows(
                session, settings=self.settings, now=now
            ):
                # Re-read under our own session: the row may have been sent or
                # cancelled since the query.
                user = await session.get(User, user_id)
                if user is None:
                    await mark_delivery_failed(
                        session, delivery_id=delivery_id, error_code="user_not_found", terminal=True
                    )
                    counters["cancelled"] += 1
                    continue
                if not await claim_delivery(
                    session,
                    delivery_id=delivery_id,
                    worker_id=self.worker_id,
                    now=now,
                    lease_seconds=self.settings.lease_seconds,
                ):
                    continue
                await session.commit()

                try:
                    if kind == WEEKLY_MIRROR:
                        week = str(now.strftime("%G-W%V"))
                        reason = await send_weekly_mirror(
                            self.bot, self.cfg, user, session, week, self.analytics
                        )
                    else:
                        reason = await send_daily_push(
                            self.bot, self.cfg, user, session, now.date().isoformat()
                        )
                except Exception as exc:  # noqa: BLE001 - one bad send must not stop the batch
                    logger.warning("push delivery %s raised: %s", delivery_id, exc)
                    reason = classify_push_error(exc)

                if reason is None:
                    if await mark_delivery_sent(session, delivery_id=delivery_id, now=utcnow()):
                        counters["sent"] += 1
                else:
                    # "Nothing to send" and "permanently rejected" are both closed
                    # rather than retried: the work is done or will never succeed.
                    terminal = reason in PUSH_TERMINAL_CODES or reason in PUSH_SKIP_CODES
                    if await mark_delivery_failed(
                        session, delivery_id=delivery_id, error_code=reason, terminal=terminal
                    ):
                        counters["cancelled" if terminal else "failed"] += 1
                await session.commit()
        return counters

    async def run_forever(self, interval_seconds: int) -> None:
        """Drive :meth:`tick` on a fixed interval, surviving individual failures."""
        while True:
            try:
                counters = await self.tick()
                if any(counters.values()):
                    logger.info("push worker tick: %s", counters)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - a bad tick must not kill the loop
                logger.warning("push worker tick failed: %s", exc)
            await asyncio.sleep(interval_seconds)


