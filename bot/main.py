from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand
from sqlalchemy import or_, select

from .config import Config, load_config
from .db import User, close_db, init_db

from .db.database import get_session
from .handlers import admin, features, payment, reading, start, voice
from .handlers.features import send_daily_push, send_weekly_mirror
from .services.analytics import Analytics

logger = logging.getLogger(__name__)

_lock_handle = None


def _acquire_single_instance_lock() -> bool:
    """Return True if this process owns the lock, False if another instance runs."""
    global _lock_handle
    # Legacy .bot.lock can remain unreleasable on Windows after a forced process termination.
    # A versioned runtime lock lets the current release recover while retaining an exclusive guard.
    lock_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".bot.runtime.lock")

    try:
        _lock_handle = open(lock_path, "w")
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_handle.write(str(os.getpid()))
        _lock_handle.flush()
        return True
    except OSError:
        if _lock_handle is not None:
            _lock_handle.close()
            _lock_handle = None
        return False

PUSH_HOUR_UTC = 6  # ~09:00 MSK
PUSH_INTERVAL_SEC = 20 * 60
PUSH_BATCH = 30


def _init_sentry(cfg: Config) -> None:
    if not cfg.sentry_dsn:
        return
    try:
        import sentry_sdk

        def _scrub_sensitive(event):
            # Remove request bodies, cookies and headers.
            request = event.get("request")
            if request:
                request.pop("data", None)
                request.pop("cookies", None)
                request.pop("headers", None)
            # Redact exception messages which may contain user questions or prompts.
            for entry in event.get("exception", {}).get("values", []):
                if entry.get("value"):
                    entry["value"] = "<redacted>"
            # Drop breadcrumbs and user PII.
            event.pop("breadcrumbs", None)
            user = event.get("user")
            if user:
                user.pop("username", None)
                user.pop("email", None)
                user.pop("ip_address", None)
            return event

        def before_send(event, _hint):
            try:
                return _scrub_sensitive(event)
            except Exception:  # noqa: BLE001
                return event

        sentry_sdk.init(
            dsn=cfg.sentry_dsn,
            environment=os.getenv("ENVIRONMENT", "production"),
            release=os.getenv("RELEASE_TAG", "dev"),
            before_send=before_send,
        )
        logger.info("Sentry enabled")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Sentry init failed: %s", exc)


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Меню / Menu"),
            BotCommand(command="help", description="Помощь / Help"),
        ]
    )


async def daily_push_loop(bot: Bot, cfg: Config, analytics: Analytics) -> None:
    """Each morning sends the personal altar; on Sundays also the weekly mirror."""
    while True:
        try:
            now = datetime.now(timezone.utc)
            if now.hour >= PUSH_HOUR_UTC:
                today_str = now.date().isoformat()
                week_str = now.strftime("%G-W%V")
                is_sunday = now.weekday() == 6
                async with get_session() as session:
                    users = (
                        (
                            await session.execute(
                                select(User).where(
                                    User.daily_push == True,  # noqa: E712
                                    or_(User.last_push_date.is_(None), User.last_push_date != today_str),
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    sent = 0
                    for u in users:
                        if sent >= PUSH_BATCH:
                            break
                        try:
                            if await send_daily_push(bot, cfg, u, session, today_str):
                                sent += 1
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("push to %s failed: %s", u.id, exc)
                    if is_sunday:
                        mirror_users = (
                            (
                                await session.execute(
                                    select(User).where(
                                        User.daily_push == True,  # noqa: E712
                                        or_(User.last_mirror_week.is_(None), User.last_mirror_week != week_str),
                                    )
                                )
                            )
                            .scalars()
                            .all()
                        )
                        for u in mirror_users:
                            try:
                                await send_weekly_mirror(bot, cfg, u, session, week_str, analytics)
                            except Exception as exc:  # noqa: BLE001
                                logger.warning("mirror to %s failed: %s", u.id, exc)
                    await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("daily push loop error: %s", exc)
        await asyncio.sleep(PUSH_INTERVAL_SEC)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not _acquire_single_instance_lock():
        logger.info("Another instance is already running — exiting cleanly.")
        return
    cfg: Config = load_config(require_token=True)
    _init_sentry(cfg)
    await init_db(cfg.database_url or cfg.db_path)

    # --- agent-core: initialize HarnessState ---
    try:
        from .agent import init_harness
        await init_harness()
        logger.info("agent-core HarnessState initialized")
    except Exception as exc:  # noqa: BLE001
        logger.warning("agent-core init failed (non-blocking): %s", exc)

    analytics = Analytics(cfg)
    bot = Bot(
        token=cfg.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp["cfg"] = cfg
    dp["analytics"] = analytics

    dp.include_routers(start.router, voice.router, reading.router, payment.router, admin.router, features.router)

    try:
        await set_commands(bot)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram command registration skipped: %s", exc)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram webhook cleanup skipped: %s", exc)
    logger.info("Starting polling as %s…", cfg.bot_display_name)

    push_task = asyncio.create_task(daily_push_loop(bot, cfg, analytics))
    try:
        while True:
            try:
                await dp.start_polling(bot)
                break
            except TelegramAPIError as exc:
                logger.warning("Telegram polling stopped; retrying in 10s: %s", exc)
                await asyncio.sleep(10)
    finally:
        push_task.cancel()
        analytics.shutdown()
        # --- agent-core: close harness ---
        try:
            from .agent import close_harness
            await close_harness()
        except Exception:  # noqa: BLE001
            pass
        await bot.session.close()
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
