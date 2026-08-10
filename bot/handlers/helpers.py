from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from sqlalchemy import func, select
from aiogram.types import User as TgUser

from ..config import Config
from ..db.database import get_session
from ..db.models import User
from ..i18n import detect_language

REF_PREFIX = "ref_"
REFERRAL_VARIANTS = frozenset({"a", "b"})
_REFERRAL_PARAM_RE = re.compile(r"^ref_([1-9]\d*)(?:_([a-z]))?$")


def parse_referral_attribution(param: str | None, own_id: int) -> tuple[int, str | None] | None:
    """Extract a referrer and optional share-caption experiment variant."""
    if not param:
        return None
    match = _REFERRAL_PARAM_RE.fullmatch(param)
    if match is None:
        return None
    ref_id = int(match.group(1))
    variant = match.group(2)
    if ref_id == own_id or variant not in {None, *REFERRAL_VARIANTS}:
        return None
    return ref_id, variant


def parse_referral_param(param: str | None, own_id: int) -> int | None:
    """Extract referrer id from a /start deep link param like 'ref_12345'."""
    attribution = parse_referral_attribution(param, own_id)
    return attribution[0] if attribution else None


async def get_or_create_user(
    tg_user: TgUser,
    cfg: Config,
    referred_by: int | None = None,
    referral_variant: str | None = None,
) -> User:
    user, _ = await get_or_create_user_with_status(
        tg_user, cfg, referred_by=referred_by, referral_variant=referral_variant
    )
    return user


async def get_or_create_user_with_status(
    tg_user: TgUser,
    cfg: Config,
    referred_by: int | None = None,
    referral_variant: str | None = None,
) -> tuple[User, bool]:
    """Create a user once and expose whether this was a new referral signup."""
    variant = referral_variant if referral_variant in REFERRAL_VARIANTS else None
    async with get_session() as session:
        user = await session.get(User, tg_user.id)
        if user is None:
            lang = detect_language(tg_user.language_code)
            total = (
                await session.execute(select(func.count()).select_from(User))
            ).scalar_one()
            bonus = cfg.earlybird_bonus if total < cfg.earlybird_limit else 0
            user = User(
                id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                language=lang,
                free_readings=cfg.free_readings + bonus,
                referred_by=referred_by,
                referral_variant=variant,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user, True
        else:
            changed = False
            if user.username != tg_user.username:
                user.username = tg_user.username
                changed = True
            if user.first_name != tg_user.first_name:
                user.first_name = tg_user.first_name
                changed = True
            if changed:
                await session.commit()
        return user, False


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_unlimited(user: User, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    until = ensure_utc(user.unlimited_until)
    return bool(until and until > now)


def redeemed_codes(user: User) -> list[str]:
    try:
        return json.loads(user.redeemed_promos or "[]")
    except Exception:
        return []
