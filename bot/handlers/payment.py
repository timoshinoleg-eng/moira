from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, LabeledPrice, Message
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..config import Config
from ..db.database import get_session
from ..db.models import Payment, PromoCode, PromoRedemption, Referral, User
from ..i18n import t
from ..keyboards import back_menu_kb, invite_menu_kb, main_menu_kb, paywall_kb, tariffs_kb
from ..payments import PRODUCTS, parse_payload, payload_for
from ..services.analytics import Analytics
from .growth import invite_variant, referral_deeplink, telegram_share_url
from .helpers import ensure_utc, get_or_create_user, redeemed_codes

router = Router()

INV_NAME = {"reading_1": "reading", "unlimited_7": "week", "unlimited_30": "month"}

CANCEL_TOKENS = {"/start", "start", "меню", "menu"}


class PromoStates(StatesGroup):
    waiting_code = State()


@router.callback_query(F.data == "tariffs")
async def cb_tariffs(callback: CallbackQuery, cfg: Config, analytics: Analytics) -> None:
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    await analytics.track(user.id, "paywall_viewed", source="tariffs")
    await callback.message.answer(t(lang, "tariffs_title"), reply_markup=tariffs_kb(lang))
    await callback.answer()


@router.callback_query(F.data == "invite")
async def cb_invite(callback: CallbackQuery, cfg: Config, analytics: Analytics) -> None:
    """Single active invite route with native share and stable attribution."""
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    try:
        me = await callback.bot.me()
        variant = invite_variant(user.id)
        link = referral_deeplink(me.username or "", user.id, variant)
    except Exception:  # noqa: BLE001 - keep invite failure user-safe
        await callback.answer(t(lang, "invite_link_unavailable"), show_alert=True)
        return

    share_copy = t(lang, "invite_share_copy")
    share_url = telegram_share_url(share_copy, link)
    await analytics.track(user.id, "invite_viewed", caption_variant=variant)
    message = "\n\n".join(
        (
            t(lang, "invite_title"),
            t(lang, "invite_body", reward=cfg.referral_reward),
            f"<code>{link}</code>",
        )
    )
    await callback.message.answer(
        message,
        reply_markup=invite_menu_kb(lang, share_url),
        disable_web_page_preview=True,
    )
    await callback.answer()
@router.callback_query(F.data.startswith("pay:"))
async def cb_pay(callback: CallbackQuery, cfg: Config, analytics: Analytics) -> None:
    product = PRODUCTS.get(callback.data.split(":", 1)[1])
    if product is None:
        await callback.answer("?")
        return
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    inv = INV_NAME[product.id]
    await analytics.track(user.id, "invoice_created", product=product.id, stars=product.xtr)
    await callback.bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=t(lang, f"inv_title_{inv}"),
        description=t(lang, f"inv_desc_{inv}"),
        payload=payload_for(product.id),
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=t(lang, f"inv_label_{inv}"), amount=product.xtr)],
        subscription_period=30 * 24 * 3600 if product.subscription else None,
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query, cfg: Config) -> None:
    product = parse_payload(pre_checkout_query.invoice_payload)
    if (
        product
        and pre_checkout_query.currency == "XTR"
        and pre_checkout_query.total_amount == product.xtr
    ):
        await pre_checkout_query.answer(ok=True)
    else:
        await pre_checkout_query.answer(ok=False, error_message="Bad invoice")


@router.message(F.successful_payment)
async def on_payment(message: Message, cfg: Config, analytics: Analytics) -> None:
    """Idempotent payment granter: a duplicated successful_payment never grants twice.

    Server-side product catalog is the single source of truth for price and entitlement.
    """
    sp = message.successful_payment
    product = parse_payload(sp.invoice_payload)
    user = await get_or_create_user(message.from_user, cfg)
    lang = user.language
    now = datetime.now(timezone.utc)

    if (
        product is None
        or sp.currency != "XTR"
        or sp.total_amount != product.xtr
    ):
        await analytics.track(user.id, "payment_rejected", reason="bad_payload_or_amount")
        return

    charge_id = sp.telegram_payment_charge_id
    ref_reward = 0
    first_payment = False
    async with get_session() as session:
        u = await session.get(User, user.id)
        # Idempotent INSERT: unique constraint on charge_id makes duplicates fail safely.
        try:
            session.add(
                Payment(
                    user_id=user.id,
                    product=product.id,
                    stars=sp.total_amount,
                    charge_id=charge_id,
                    status="paid",
                )
            )
            await session.flush()
        except IntegrityError:
            await session.rollback()
            return  # duplicate charge — entitlement already granted

        prior_payments = await session.scalar(
            select(func.count()).select_from(Payment).where(Payment.user_id == user.id)
        )
        first_payment = prior_payments == 1  # this new row is the first payment

        if product.kind == "readings":
            u.free_readings += product.amount
        else:
            current = ensure_utc(u.unlimited_until)
            base = max(current, now) if current else now
            u.unlimited_until = base + timedelta(days=product.amount)

        if first_payment and u.referred_by and u.referred_by != u.id:
            already = await session.scalar(select(Referral.id).where(Referral.referred_id == u.id))
            if already is None:
                referrer = await session.get(User, u.referred_by)
                if referrer is not None:
                    referrer.free_readings += cfg.referral_reward
                    ref_reward = cfg.referral_reward
                    session.add(Referral(referrer_id=u.referred_by, referred_id=u.id, rewarded=True))

        await session.commit()
        await session.refresh(u)

    await analytics.track(
        user.id,
        "payment_succeeded",
        product=product.id,
        stars=sp.total_amount,
        first_payment=first_payment,
    )
    if ref_reward:
        await analytics.track(user.id, "referral_activated", reward=ref_reward)

    if product.kind == "readings":
        extra = t(lang, "payment_ok_reading")
    else:
        extra = t(lang, "payment_ok_days", date=u.unlimited_until.strftime(t(lang, "date_fmt")))
    await message.answer(t(lang, "payment_ok") + "\n" + extra, reply_markup=main_menu_kb(lang))


@router.message(F.refunded_payment)
async def on_refund(message: Message, cfg: Config, analytics: Analytics) -> None:
    """Idempotent refund handler. Revokes entitlement only for the original payment row."""
    rp = message.refunded_payment
    product = parse_payload(rp.invoice_payload)
    if product is None:
        return
    lang = "ru"
    async with get_session() as session:
        payment = await session.scalar(
            select(Payment).where(Payment.charge_id == rp.telegram_payment_charge_id)
        )
        if payment is not None and payment.status == "refunded":
            return  # duplicate refund notification — nothing to revoke
        u = await session.get(User, message.from_user.id)
        if u:
            lang = u.language
            if payment is not None:
                # Only revoke if we have a matching paid row.
                if product.kind == "readings":
                    u.free_readings = max(0, u.free_readings - product.amount)
                else:
                    u.unlimited_until = None
                payment.status = "refunded"
                session.add(payment)
        elif payment is not None:
            # User missing but payment row exists — mark refunded for audit.
            payment.status = "refunded"
            session.add(payment)
        await session.commit()
    await analytics.track(message.from_user.id, "payment_refunded", product=product.id)
    await message.answer(t(lang, "refund_note"))


@router.callback_query(F.data == "promo:start")
async def cb_promo(callback: CallbackQuery, state: FSMContext, cfg: Config) -> None:
    user = await get_or_create_user(callback.from_user, cfg)
    await callback.message.answer(t(user.language, "promo_prompt"), reply_markup=back_menu_kb(user.language))
    await state.set_state(PromoStates.waiting_code)
    await callback.answer()


@router.message(PromoStates.waiting_code)
async def process_promo(message: Message, state: FSMContext, cfg: Config, analytics: Analytics) -> None:
    await state.clear()
    user = await get_or_create_user(message.from_user, cfg)
    lang = user.language
    code = (message.text or "").strip().upper()
    if code.lower() in CANCEL_TOKENS:
        await message.answer(t(lang, "menu_help"), reply_markup=main_menu_kb(lang))
        return

    async with get_session() as session:
        promo = (
            await session.execute(select(PromoCode).where(func.upper(PromoCode.code) == code))
        ).scalar_one_or_none()
        if promo is None or (promo.max_uses and promo.used_count >= promo.max_uses):
            await message.answer(t(lang, "promo_invalid"), reply_markup=main_menu_kb(lang))
            return
        redeemed = redeemed_codes(user)
        if promo.code in redeemed:
            await message.answer(t(lang, "promo_used"), reply_markup=main_menu_kb(lang))
            return
        u = await session.get(User, user.id)
        redeemed.append(promo.code)
        u.redeemed_promos = json.dumps(redeemed, ensure_ascii=False)
        if promo.kind == "readings":
            u.promo_readings += promo.amount
        else:
            now = datetime.now(timezone.utc)
            current = ensure_utc(u.unlimited_until)
            base = max(current, now) if current else now
            u.unlimited_until = base + timedelta(days=promo.amount)
        promo.used_count += 1
        session.add(PromoRedemption(user_id=user.id, promo_id=promo.id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await message.answer(t(lang, "promo_used"), reply_markup=main_menu_kb(lang))
            return
        await session.refresh(u)
    await analytics.track(user.id, "promo_redeemed", kind=promo.kind, amount=promo.amount)
    if promo.kind == "readings":
        await message.answer(t(lang, "promo_ok_readings", n=promo.amount), reply_markup=main_menu_kb(lang))
    else:
        await message.answer(t(lang, "promo_ok_days", n=promo.amount), reply_markup=main_menu_kb(lang))
