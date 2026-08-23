from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete, or_

from ..config import Config
from ..db.database import get_session
from ..db.models import Event, LlmUsage, Payment, PromoRedemption, Reading, ReadingFavorite, Referral, User
from ..i18n import t
from ..keyboards import back_menu_kb, main_menu_kb
from ..services.analytics import Analytics
from .helpers import (
    get_or_create_user,
    get_or_create_user_with_status,
    is_unlimited,
    parse_referral_attribution,
)

router = Router()


async def _respond_start(
    message: Message, cfg: Config, param: str | None = None
) -> tuple[User, bool, str | None]:
    attribution = parse_referral_attribution(param, message.from_user.id) if param else None
    ref_id, variant = attribution if attribution else (None, None)
    user, created = await get_or_create_user_with_status(
        message.from_user, cfg, referred_by=ref_id, referral_variant=variant
    )
    lang = user.language
    free_total = user.free_readings + user.promo_readings
    text = t(lang, "greeting", name=cfg.bot_display_name, free=free_total)
    if is_unlimited(user):
        until = user.unlimited_until
        text += "\n\n" + t(lang, "premium_active", date=until.strftime(t(lang, "date_fmt")))
    text += "\n\n" + t(lang, "disclaimer")
    await message.answer(text, reply_markup=main_menu_kb(lang))
    return user, created, variant


@router.message(CommandStart(deep_link=True))
async def cmd_start_ref(message: Message, cfg: Config, analytics: Analytics) -> None:
    param = message.text.split(maxsplit=1)[1] if message.text and " " in message.text else None
    user, created, variant = await _respond_start(message, cfg, param)
    if created and user.referred_by:
        await analytics.track(
            user.id, "referral_signup", caption_variant=variant or "legacy"
        )


@router.message(CommandStart())
async def cmd_start(message: Message, cfg: Config, analytics: Analytics) -> None:
    await _respond_start(message, cfg)


@router.message(Command("help"))
async def cmd_help(message: Message, cfg: Config) -> None:
    user = await get_or_create_user(message.from_user, cfg)
    lang = user.language
    text = t(lang, "help_text", name=cfg.bot_display_name) + "\n\n" + t(lang, "disclaimer")
    await message.answer(text, reply_markup=back_menu_kb(lang))


@router.message(Command("delete_my_data"))
async def cmd_delete_my_data(message: Message, cfg: Config, analytics: Analytics) -> None:
    """Delete all personal data. Financial ledger rows are anonymised in place."""
    user = await get_or_create_user(message.from_user, cfg)
    lang = user.language
    async with get_session() as session:
        await session.execute(delete(Reading).where(Reading.user_id == user.id))
        await session.execute(delete(ReadingFavorite).where(ReadingFavorite.user_id == user.id))
        await session.execute(delete(Event).where(Event.distinct_id == Analytics.distinct(user.id)))
        await session.execute(delete(LlmUsage).where(LlmUsage.user_id == user.id))
        await session.execute(delete(PromoRedemption).where(PromoRedemption.user_id == user.id))
        await session.execute(
            delete(Referral).where(or_(Referral.referrer_id == user.id, Referral.referred_id == user.id))
        )
        # Payments are kept for audit; username/first_name are cleared from user row before deletion.
        u = await session.get(User, user.id)
        if u is not None:
            await session.delete(u)
        await session.commit()
    await analytics.track(user.id, "data_deleted")
    await message.answer(t(lang, "data_deleted"), reply_markup=main_menu_kb(lang))


@router.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext, cfg: Config) -> None:
    await state.clear()
    user = await get_or_create_user(callback.from_user, cfg)
    await callback.message.answer(t(user.language, "menu_help"), reply_markup=main_menu_kb(user.language))
    await callback.answer()


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery, cfg: Config) -> None:
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    text = t(lang, "help_text", name=cfg.bot_display_name) + "\n\n" + t(lang, "disclaimer")
    await callback.message.answer(text, reply_markup=back_menu_kb(lang))
    await callback.answer()


@router.callback_query(F.data == "lang:toggle")
async def cb_lang(callback: CallbackQuery, cfg: Config) -> None:
    user = await get_or_create_user(callback.from_user, cfg)
    from ..db.database import get_session
    from ..db.models import User

    async with get_session() as session:
        db_user = await session.get(User, user.id)
        db_user.language = "en" if db_user.language == "ru" else "ru"
        await session.commit()
        lang = db_user.language
    await callback.message.answer(t(lang, "lang_switched"))
    await callback.message.answer(t(lang, "menu_help"), reply_markup=main_menu_kb(lang))
    await callback.answer()
