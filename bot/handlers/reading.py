from __future__ import annotations

import asyncio
import html
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import select, update

from ..config import Config
from ..db.database import get_session
from ..db.models import Reading, User
from ..i18n import t
from ..keyboards import back_menu_kb, main_menu_kb, paywall_kb, reading_footer_kb
from ..llm import interpret_reading
from ..services.analytics import Analytics
from ..tarot import SPREADS, draw
from ..tarot.deck import cards_from_codes
from ..tarot.fallback import compose_fallback_reading
from ..visual.render import make_share_image, make_spread_image
from ..voice.speaker import synthesize_reading_voice
from .helpers import get_or_create_user, is_unlimited

logger = logging.getLogger(__name__)
router = Router()

CANCEL_TOKENS = {"/start", "start", "меню", "menu", "-cancel"}

SAFETY_PATTERNS = [
    # medical
    "диагноз", "болезнь", "рак", "опухол", "вич", "гепатит", "беременн",
    "боли", "таблетк", "лекарств", "врач", "хирург", "больниц", "препарат",
    "diagnose", "disease", "cancer", "tumor", "pregnant", "pregnancy", "medicine",
    "pill", "doctor", "hospital", "symptom", "treatment",
    # legal
    "суд", "адвокат", "закон", "юрист", "развод", "алимент", "наследств",
    "court", "lawyer", "lawsuit", "divorce", "inheritance", "legal",
    # financial
    "инвестиции", "акции", "крипт", "форекс", "брокер", "доход", "налог",
    "invest", "stock", "crypto", "forex", "broker", "tax", "finance",
    # crisis / harm
    "суицид", "убийств", "насили", "смерть", "умру", "умереть", "повешусь",
    "suicide", "kill", "murder", "violence", "death", "die", "harm",
    # prompt injection
    "ignore previous", "system prompt", "print instructions", "выведи инструкции",
    "выдай системный", "игнорируй предыдущие", "раскрой промпт", "prompt injection",
]


def _is_safety_refusal_required(question: str) -> bool:
    low = question.lower()
    return any(p in low for p in SAFETY_PATTERNS)


class ReadingStates(StatesGroup):
    waiting_question = State()


@router.callback_query(F.data.startswith("spread:"))
async def cb_spread(callback: CallbackQuery, state: FSMContext, cfg: Config, analytics: Analytics) -> None:
    spread_id = callback.data.split(":", 1)[1]
    if spread_id not in SPREADS:
        await callback.answer("?")
        return
    user = await get_or_create_user(callback.from_user, cfg)
    await analytics.track(user.id, "spread_started", spread=spread_id)
    await callback.message.answer(t(user.language, "ask_question"), reply_markup=back_menu_kb(user.language))
    await state.set_state(ReadingStates.waiting_question)
    await state.update_data(spread_id=spread_id)
    await callback.answer()


@router.message(ReadingStates.waiting_question)
async def process_reading(message: Message, state: FSMContext, cfg: Config, analytics: Analytics) -> None:
    data = await state.get_data()
    await state.clear()
    spread_id = data.get("spread_id")
    if spread_id not in SPREADS:
        return

    user = await get_or_create_user(message.from_user, cfg)
    lang = user.language
    question = (message.text or "").strip()

    if question.lower() in CANCEL_TOKENS:
        await message.answer(t(lang, "menu_help"), reply_markup=main_menu_kb(lang))
        return

    if question and _is_safety_refusal_required(question):
        await analytics.track(user.id, "safety_refusal", spread=spread_id)
        await message.answer(t(lang, "safety_refusal"), reply_markup=main_menu_kb(lang))
        return

    reason = await _consume_reading(user)
    if reason is None:
        await analytics.track(user.id, "paywall_viewed", spread=spread_id)
        await message.answer(
            t(lang, "paywall_text") + "\n\n" + t(lang, "tariffs_title"),
            reply_markup=paywall_kb(lang),
        )
        return

    status_msg = await message.answer(t(lang, "shuffling"))
    await asyncio.sleep(1.2)

    drawn: list = []
    result = None
    try:
        drawn = draw(spread_id)
        spread_title = SPREADS[spread_id]["title"][lang]

        cards_info = [
            {
                "label": d.position_label.get(lang, d.position_label["ru"]),
                "card": d.card,
                "reversed": d.reversed,
                "name": d.card.name(lang),
            }
            for d in drawn
        ]
        photo_bytes = await asyncio.to_thread(make_spread_image, spread_title, cards_info, "MOIRA ✦ TAROT")

        caption_lines = [f"🔮 <b>{html.escape(spread_title)}</b>"]
        if question and question != "-":
            caption_lines.append(html.escape(t(lang, "question_line", q=question[:300])))
        for info in cards_info:
            mark = t(lang, "rev_mark") if info["reversed"] else ""
            caption_lines.append(f"• {html.escape(info['label'])}: <b>{html.escape(info['name'])}{mark}</b>")
        await message.answer_photo(
            BufferedInputFile(photo_bytes, filename="spread.jpg"),
            caption="\n".join(caption_lines),
        )

        result = await interpret_reading(
            cfg, lang, spread_title, question or None, drawn, user_id=user.id, spread_id=spread_id
        )
        if result:
            parts = [f"<b>{html.escape(result.headline or t(lang, 'spread_interpretation_header'))}</b>"]
            if result.opening:
                parts.append(f"<i>{html.escape(result.opening)}</i>")
            plain_parts = []
            for info, interp in zip(cards_info, result.card_interpretations):
                label = info["label"]
                text_interp = interp.core_message
                parts.append(f"<i>{html.escape(label)}:</i> <tg-spoiler>{html.escape(text_interp)}</tg-spoiler>")
                plain_parts.append(f"{label}: {text_interp}")
            parts.append(f"<b>{html.escape(t(lang, 'spread_synthesis_header'))}</b>")
            parts.append(f"<tg-spoiler>{html.escape(result.synthesis)}</tg-spoiler>")
            if result.practical_focus:
                parts.append(f"<i>{html.escape(result.practical_focus)}</i>")
            parts.append(f"<i>✦ {html.escape(result.reflection_question)}</i>")
            plain_parts.append(result.synthesis)
            text = "\n".join(parts)
            plain = ". ".join(plain_parts)
            voice_text = html.unescape(f"{result.headline}. {result.voice_summary}")
        else:
            fallback = compose_fallback_reading(lang, spread_id, drawn)
            parts = [f"<b>{html.escape(fallback['headline'])}</b>"]
            if fallback["opening"]:
                parts.append(f"<i>{html.escape(fallback['opening'])}</i>")
            for card_text in fallback["card_texts"]:
                parts.append(f"<tg-spoiler>{card_text}</tg-spoiler>")
            parts.append(f"<b>{html.escape(t(lang, 'spread_synthesis_header'))}</b>")
            parts.append(f"<tg-spoiler>{html.escape(fallback['synthesis'])}</tg-spoiler>")
            if fallback["practical_focus"]:
                parts.append(f"<i>{html.escape(fallback['practical_focus'])}</i>")
            parts.append(f"<i>✦ {html.escape(fallback['reflection_question'])}</i>")
            text = "\n".join(parts)
            plain = fallback["plain_text"]
            if not cfg.openrouter_api_key:
                parts.append(html.escape(t(lang, "template_note")))
            await analytics.track(user.id, "llm_fallback_used", spread=spread_id)
            voice_text = html.unescape(fallback["voice_text"])
        await message.answer(text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("reading generation failed for user %s: %s", user.id, exc)
        await _compensate_reading(user, reason)
        try:
            await status_msg.edit_text(t(lang, "reading_failed"))
        except Exception:  # noqa: BLE001
            await message.answer(t(lang, "reading_failed"))
        await analytics.track(user.id, "spread_failed", spread=spread_id, error=type(exc).__name__)
        return

    audio = await synthesize_reading_voice(voice_text, lang)
    if audio:
        await _send_voice_or_audio(message, audio, lang)

    reading_id = 0
    async with get_session() as session:
        row = Reading(
            user_id=user.id,
            spread=spread_id,
            cards_json=",".join(f"{d.card.id}{'R' if d.reversed else ''}" for d in drawn),
            question=question[:500] if question and question != "-" else None,
            interpretation=(plain)[:3900],
        )
        session.add(row)
        await session.commit()
        reading_id = row.id
    await analytics.track(user.id, "spread_completed", spread=spread_id, ai=bool(result))

    footer_lines = []
    if reason == "unlimited":
        until = user.unlimited_until
        footer_lines.append(t(lang, "premium_active", date=until.strftime(t(lang, "date_fmt"))))
    else:
        footer_lines.append(t(lang, "free_left", n=user.free_readings + user.promo_readings))
    footer_lines.append(t(lang, "disclaimer"))
    await status_msg.edit_text("\n".join(footer_lines), reply_markup=main_menu_kb(lang))

    if reading_id:
        await message.answer(
            t(lang, "reading_actions"), reply_markup=reading_footer_kb(lang, reading_id)
        )


@router.callback_query(F.data.startswith("share:"))
async def cb_share(callback: CallbackQuery, cfg: Config, analytics: Analytics) -> None:
    try:
        reading_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("?")
        return
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    async with get_session() as session:
        reading = await session.get(Reading, reading_id)
    if reading is None or reading.user_id != user.id:
        await callback.answer(t(lang, "history_empty"))
        return
    pairs = cards_from_codes(reading.cards_json.split(","))
    if not pairs:
        await callback.answer("?")
        return
    spread_title = SPREADS[reading.spread]["title"][lang] if reading.spread in SPREADS else "Tarot"
    positions = SPREADS[reading.spread]["positions"] if reading.spread in SPREADS else []
    cards_info = []
    for i, (card, rev) in enumerate(pairs):
        if i < len(positions):
            label = positions[i][1].get(lang, positions[i][1]["ru"])
        else:
            label = str(i + 1)
        cards_info.append({"label": label, "card": card, "reversed": rev, "name": card.name(lang)})
    summary = (reading.interpretation or "").strip().replace("\n", " ")[:180]
    me = await callback.bot.me()
    bot_username = me.username or ""
    link = f"https://t.me/{bot_username}?start=ref_{user.id}" if bot_username else ""
    photo = await asyncio.to_thread(make_share_image, spread_title, cards_info, summary, cfg.bot_display_name)
    await callback.message.answer_photo(
        BufferedInputFile(photo, filename="share.jpg"),
        caption=html.escape(t(lang, "share_caption", link=link)),
    )
    await analytics.track(user.id, "share_created", spread=reading.spread)
    await callback.answer()


async def _send_voice_or_audio(message: Message, audio: bytes, lang: str) -> None:
    """Try voice note first, then audio file, then a localized notice."""
    try:
        await message.answer_voice(BufferedInputFile(audio, filename="moira_voice.mp3"))
        return
    except TelegramBadRequest as exc:
        if "VOICE_MESSAGES_FORBIDDEN" in str(exc):
            logger.info("voice messages forbidden for user %s", message.from_user.id)
        else:
            logger.warning("voice send bad request: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("voice send failed: %s", exc)

    try:
        await message.answer_audio(
            BufferedInputFile(audio, filename="moira_voice.mp3"),
            title=t(lang, "voice_title"),
        )
        return
    except Exception as exc:  # noqa: BLE001
        logger.warning("audio fallback failed: %s", exc)

    await message.answer(t(lang, "voice_unavailable"))


async def _consume_reading(user: User) -> str | None:
    """Deduct a reading credit atomically if possible.

    Returns reason string or None when paywall is needed.
    Deduction order: promo -> free -> unlimited (no deduction).
    """
    async with get_session() as session:
        u = await session.get(User, user.id)
        if is_unlimited(u):
            return "unlimited"

        # 1. promo readings
        result = await session.execute(
            update(User)
            .where(User.id == user.id, User.promo_readings > 0)
            .values(promo_readings=User.promo_readings - 1)
        )
        if result.rowcount == 1:
            await session.commit()
            user.promo_readings = max(0, user.promo_readings - 1)
            return "promo"

        # 2. free readings
        result = await session.execute(
            update(User)
            .where(User.id == user.id, User.free_readings > 0)
            .values(free_readings=User.free_readings - 1)
        )
        if result.rowcount == 1:
            await session.commit()
            user.free_readings = max(0, user.free_readings - 1)
            return "free"

        return None


async def _compensate_reading(user: User, reason: str | None) -> None:
    """Idempotently refund a consumed reading credit when generation failed."""
    if reason is None or reason == "unlimited":
        return
    async with get_session() as session:
        u = await session.get(User, user.id)
        if u is None:
            return
        if reason == "promo":
            u.promo_readings += 1
        elif reason == "free":
            u.free_readings += 1
        await session.commit()
