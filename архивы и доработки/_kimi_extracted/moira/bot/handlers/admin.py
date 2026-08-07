from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.sql import and_

from ..config import Config
from ..db.database import get_session
from ..db.models import Payment, PromoCode, Reading, User

router = Router()


def _is_admin(user_id: int, cfg: Config) -> bool:
    return user_id in cfg.admin_ids


@router.message(Command("stats"))
async def cmd_stats(message: Message, cfg: Config) -> None:
    if not _is_admin(message.from_user.id, cfg):
        return
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    async with get_session() as session:
        users_total = (await session.execute(select(func.count()).select_from(User))).scalar_one()
        readings_total = (await session.execute(select(func.count()).select_from(Reading))).scalar_one()
        payments = (await session.execute(select(func.count().select_from(Payment), func.sum(Payment.stars)))).one()
        payments_total, stars_total = payments[0], payments[1] or 0
        readings_today = (
            await session.execute(
                select(func.count()).select_from(Reading).where(Reading.created_at >= today_start)
            )
        ).scalar_one()
        users_today = (
            await session.execute(
                select(func.count()).select_from(User).where(User.created_at >= today_start)
            )
        ).scalar_one()
    text = (
        f"👥 Пользователей: {users_total}\n"
        f"🔮 Раскладов всего: {readings_total}\n"
        f"💳 Платежей: {payments_total} ({stars_total} ⭐)\n"
        f"📅 Сегодня: +{users_today} пользователей, {readings_today} раскладов"
    )
    await message.answer(text)


@router.message(Command("promo_create"))
async def cmd_promo_create(message: Message, cfg: Config) -> None:
    if not _is_admin(message.from_user.id, cfg):
        return
    parts = (message.text or "").split()
    if len(parts) != 4:
        await message.answer("Использование: /promo_create <readings|days> <amount> <CODE>\nПример: /promo_create readings 5 WELCOME5")
        return
    kind, amount_s, code = parts[1], parts[2], parts[3].strip().upper()
    if kind not in ("readings", "days"):
        await message.answer("kind должен быть readings или days")
        return
    try:
        amount = int(amount_s)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("amount должен быть целым > 0")
        return
    async with get_session() as session:
        exists = (
            await session.execute(select(PromoCode).where(PromoCode.code == code))
        ).scalar_one_or_none()
        if exists:
            await message.answer(f"Код {code} уже существует ({exists.kind} {exists.amount})")
            return
        session.add(PromoCode(code=code, kind=kind, amount=amount))
        await session.commit()
    await message.answer(f"✅ Промокод создан: {code} → {kind} +{amount} (безлимит по числу активаций)")


@router.message(Command("promo_list"))
async def cmd_promo_list(message: Message, cfg: Config) -> None:
    if not _is_admin(message.from_user.id, cfg):
        return
    async with get_session() as session:
        promos = (await session.execute(select(PromoCode).order_by(PromoCode.id.desc()))).scalars().all()
    if not promos:
        await message.answer("Промокодов нет.")
        return
    lines = ["Промокоды:"]
    for p in promos:
        limit = p.max_uses if p.max_uses else "∞"
        lines.append(f"• {p.code}: {p.kind} +{p.amount}, активаций {p.used_count}/{limit}")
    await message.answer("\n".join(lines))


@router.message(Command("grant"))
async def cmd_grant(message: Message, cfg: Config) -> None:
    if not _is_admin(message.from_user.id, cfg):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer("Использование: /grant <user_id> <readings:N|days:N>")
        return
    try:
        target_id = int(parts[1])
        kind, amount_s = parts[2].split(":")
        amount = int(amount_s)
    except ValueError:
        await message.answer("Неверный формат.")
        return
    if kind not in ("readings", "days"):
        await message.answer("kind: readings или days")
        return
    async with get_session() as session:
        u = await session.get(User, target_id)
        if u is None:
            await message.answer("Пользователь ещё не запускал бота.")
            return
        if kind == "readings":
            u.free_readings += amount
        else:
            now = datetime.now(timezone.utc)
            current = u.unlimited_until
            if current is not None and current.tzinfo is None:
                current = current.replace(tzinfo=timezone.utc)
            base = max(current, now) if current else now
            u.unlimited_until = base + timedelta(days=amount)
        await session.commit()
    await message.answer(f"✅ Выдано: user {target_id} → {kind} +{amount}")
