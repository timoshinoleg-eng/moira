from __future__ import annotations

import asyncio
import html
import logging
import re
import secrets
from datetime import date, datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..astro.calc import (
    ELEMENT_NAMES,
    MOON_SIGN_TEXTS,
    PERSONAL_OTHER_ELEMENT,
    PERSONAL_SAME_ELEMENT,
    PHASE_NAMES,
    PHASE_TEXTS,
    ZODIAC_ELEMENT,
    ZODIAC_NAMES,
    daily_card,
    moon_state_by_date,
    sign_by_date,
)
from ..config import Config
from ..db.database import get_session
from ..db.models import Reading, ReadingFavorite, User
from ..i18n import t
from ..keyboards import altar_kb, back_menu_kb, history_kb, main_menu_kb, mirror_kb
from ..llm.adapter import weekly_mirror_text
from ..services.analytics import Analytics
from ..tarot import SPREADS
from ..tarot.deck import build_deck, cards_from_codes
from ..visual.render import make_single_image
from .helpers import ensure_utc, get_or_create_user

logger = logging.getLogger(__name__)
router = Router()

BIRTH_RE = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s*$")

from ..tarot.quiz import (
    QUIZ_QUESTIONS,
    compute_result,
    format_arcana_result,
    get_arcana_description,
)

# Backward compatibility alias
QUIZ = {
    "ru": [
        {"q": q[0][0], "a": [(a[0], 0) for a in q]}
        for q in QUIZ_QUESTIONS
    ],
    "en": [
        {"q": q[0][1], "a": [(a[1], 0) for a in q]}
        for q in QUIZ_QUESTIONS
    ],
}

DECK_BY_ID = {c.id: c for c in build_deck()}


class FeatureStates(StatesGroup):
    waiting_birth = State()
    quiz = State()


def _parse_birth_date(text: str) -> date | None:
    m = BIRTH_RE.match(text or "")
    if not m:
        return None
    day_s, month_s, year_s = m.groups()
    try:
        return date(int(year_s), int(month_s), int(day_s))
    except ValueError:
        return None


def _major_card(num: int):
    return DECK_BY_ID.get(f"major_{num}")


async def _show_altar(bot: Bot, chat_id: int, user: User, cfg: Config) -> None:
    lang = user.language
    today = date.today()
    card, rev = daily_card(today, user.id)
    phase, _illum, moon_sign = moon_state_by_date(today)

    lines = [t(lang, "altar_header", date=today.strftime(t(lang, "date_fmt")))]
    lines.append(t(lang, "altar_card", card=card.name(lang), rev=t(lang, "rev_mark") if rev else ""))
    lines.append(t(lang, "altar_phase", phase=PHASE_NAMES[lang][phase], meaning=PHASE_TEXTS[lang][phase]))
    lines.append(
        t(lang, "altar_moonin", sign=ZODIAC_NAMES[lang][moon_sign], text=MOON_SIGN_TEXTS[lang][moon_sign])
    )

    if user.birth_date:
        try:
            birth = date.fromisoformat(user.birth_date)
            user_sign = sign_by_date(birth)
            lines.append(
                t(
                    lang,
                    "altar_sun",
                    sign=ZODIAC_NAMES[lang][user_sign],
                    element=ELEMENT_NAMES[lang][ZODIAC_ELEMENT[user_sign]],
                )
            )
            if ZODIAC_ELEMENT[user_sign] == ZODIAC_ELEMENT[moon_sign]:
                lines.append(
                    PERSONAL_SAME_ELEMENT[lang].format(el=ELEMENT_NAMES[lang][ZODIAC_ELEMENT[moon_sign]])
                )
            else:
                lines.append(
                    PERSONAL_OTHER_ELEMENT[lang].format(
                        el_moon=ELEMENT_NAMES[lang][ZODIAC_ELEMENT[moon_sign]],
                        el_self=ELEMENT_NAMES[lang][ZODIAC_ELEMENT[user_sign]].lower()
                        if lang == "en"
                        else ELEMENT_NAMES[lang][ZODIAC_ELEMENT[user_sign]],
                    )
                )
        except ValueError:
            pass

    subtitle = card.name(lang) + (t(lang, "rev_mark") if rev else "")
    photo = await asyncio.to_thread(
        make_single_image,
        t(lang, "altar_header", date=today.strftime("%d.%m")),
        subtitle,
        card,
        footer="MOIRA ✦ TAROT",
        lang=lang,
        reversed_=rev,
    )
    await bot.send_photo(
        chat_id,
        BufferedInputFile(photo, filename="altar.jpg"),
        caption="\n".join(lines),
        reply_markup=altar_kb(lang, user.daily_push),
    )


@router.callback_query(F.data == "altar")
async def cb_altar(callback: CallbackQuery, state: FSMContext, cfg: Config) -> None:
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    if not user.birth_date:
        await callback.message.answer(t(lang, "altar_need_birth"))
        await state.set_state(FeatureStates.waiting_birth)
        await callback.answer()
        return
    await _show_altar(callback.bot, callback.message.chat.id, user, cfg)
    await callback.answer()


@router.message(FeatureStates.waiting_birth)
async def process_birth(message: Message, state: FSMContext, cfg: Config) -> None:
    await state.clear()
    user = await get_or_create_user(message.from_user, cfg)
    lang = user.language
    text = (message.text or "").strip()
    if text.lower() in {"/start", "menu", "меню", "start"}:
        await message.answer(t(lang, "menu_help"), reply_markup=main_menu_kb(lang))
        return
    birth = _parse_birth_date(text)
    if birth is None:
        await message.answer(t(lang, "birth_invalid"))
        await state.set_state(FeatureStates.waiting_birth)
        return
    async with get_session() as session:
        u = await session.get(User, user.id)
        u.birth_date = birth.isoformat()
        await session.commit()
        await session.refresh(u)
    await message.answer(t(lang, "birth_ok"))
    await _show_altar(message.bot, message.chat.id, u, cfg)


@router.callback_query(F.data.in_({"altar:push_on", "altar:push_off"}))
async def cb_altar_push(callback: CallbackQuery, cfg: Config) -> None:
    user = await get_or_create_user(callback.from_user, cfg)
    enable = callback.data.endswith("push_on")
    async with get_session() as session:
        u = await session.get(User, user.id)
        u.daily_push = enable
        await session.commit()
    lang = user.language
    await callback.answer(t(lang, "altar_toggle_on") if enable else t(lang, "altar_toggle_off"))


@router.callback_query(F.data == "quiz")
async def cb_quiz(callback: CallbackQuery, state: FSMContext, cfg: Config) -> None:
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    await callback.message.answer(t(lang, "quiz_intro"))
    await state.set_state(FeatureStates.quiz)
    await state.update_data(idx=0, scores={})
    await _send_question(callback.message, lang, 0)
    await callback.answer()


async def _send_question(message: Message, lang: str, idx: int) -> None:
    questions = QUIZ_QUESTIONS
    q = questions[idx]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=answer[0 if lang == "ru" else 1], callback_data=f"quiz:a:{a_idx}")]
            for a_idx, answer in enumerate(q)
        ]
    )
    q_text = q[0][0] if lang == "ru" else q[0][1]
    await message.answer(
        f"<b>{t(lang, 'quiz_progress', n=idx + 1)}</b>\n\n{q_text}",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("quiz:a:"), FeatureStates.quiz)
async def cb_quiz_answer(callback: CallbackQuery, state: FSMContext, cfg: Config) -> None:
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    answer_idx = int(callback.data.split(":")[2])
    data = await state.get_data()
    idx = int(data.get("idx", 0))
    answers: list[int] = list(data.get("answers", []))
    answers.append(answer_idx)

    if idx + 1 < len(QUIZ_QUESTIONS):
        await state.update_data(idx=idx + 1, answers=answers)
        await _send_question(callback.message, lang, idx + 1)
        await callback.answer()
        return

    # Compute result using the new scoring algorithm
    arcana_num = compute_result(answers)
    card = _major_card(arcana_num)
    arcana_name = card.name(lang) if card else str(arcana_num)
    result_text = format_arcana_result(arcana_num, lang)

    await state.clear()

    title = t(lang, "quiz_result_title", name=arcana_name)
    if card is not None:
        photo = await asyncio.to_thread(
            make_single_image, title, result_text, card, footer="MOIRA ✦ TAROT", lang=lang, reversed_=False
        )
        await callback.message.answer_photo(
            BufferedInputFile(photo, filename="arcana.jpg"),
            caption=f"<b>{title}</b>\n{result_text}",
        )
    else:
        await callback.message.answer(f"<b>{title}</b>\n{result_text}")
    await callback.message.answer(t(lang, "quiz_share"), reply_markup=back_menu_kb(lang))
    await callback.answer()


async def send_daily_push(bot: Bot, cfg: Config, user: User, session, today_str: str) -> bool:
    """Morning personal altar push. Returns True only when the message was sent successfully."""
    lang = user.language
    if not user.daily_push:
        return False
    if user.last_push_date == today_str:
        return False
    today = date.fromisoformat(today_str)
    card, rev = daily_card(today, user.id)
    phase, _illum, _msign = moon_state_by_date(today)
    text = t(
        lang,
        "push_altar",
        name=cfg.bot_display_name,
        card=card.name(lang),
        rev=t(lang, "rev_mark") if rev else "",
        phase=PHASE_NAMES[lang][phase],
        meaning=PHASE_TEXTS[lang][phase],
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_open_altar"), callback_data="altar")]
        ]
    )
    try:
        await bot.send_message(user.id, text, reply_markup=kb)
    except Exception as exc:  # noqa: BLE001
        logger.warning("daily push to %s failed: %s", user.id, exc)
        return False
    user.last_push_date = today_str
    return True


MIRROR_QUESTIONS = {
    "ru": [
        "Что из этой недели ты хочешь забрать с собой в следующую?",
        "Какая тема повторялась чаще всего — и о чём она тебе говорит?",
        "Что бы ты сказал(а) себе неделю назад?",
    ],
    "en": [
        "What from this week do you want to carry into the next one?",
        "Which theme repeated the most — and what is it telling you?",
        "What would you tell yourself from a week ago?",
    ],
}


async def _toggle_favorite(user_id: int, reading_id: int) -> bool:
    """Returns True when the reading is now a favourite.

    The operation is idempotent: a concurrent duplicate insert leaves the row in place.
    """
    async with get_session() as session:
        row = await session.scalar(
            select(ReadingFavorite).where(
                ReadingFavorite.user_id == user_id, ReadingFavorite.reading_id == reading_id
            )
        )
        if row is not None:
            await session.delete(row)
            await session.commit()
            return False
        session.add(ReadingFavorite(user_id=user_id, reading_id=reading_id))
        try:
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            # Another transaction won the race and created the row.
            return True


async def _render_history(message: Message, user: User, edit: bool = False) -> None:
    lang = user.language
    async with get_session() as session:
        readings = (
            (
                await session.execute(
                    select(Reading)
                    .where(Reading.user_id == user.id)
                    .order_by(Reading.id.desc())
                    .limit(8)
                )
            )
            .scalars()
            .all()
        )
        faved_rows = (
            (
                await session.execute(
                    select(ReadingFavorite.reading_id).where(ReadingFavorite.user_id == user.id)
                )
            )
            .scalars()
            .all()
        )
    faved = set(faved_rows)
    if not readings:
        await message.answer(t(lang, "history_empty"), reply_markup=back_menu_kb(lang))
        return
    lines = [f"<b>{t(lang, 'history_title')}</b>", ""]
    ids_labels = []
    for r in readings:
        title = SPREADS[r.spread]["title"][lang] if r.spread in SPREADS else r.spread
        names = [c.name(lang) for c, _rev in cards_from_codes(r.cards_json.split(","))][:3]
        star = "⭐ " if r.id in faved else ""
        dtxt = (ensure_utc(r.created_at) or datetime.now(timezone.utc)).strftime("%d.%m")
        lines.append(f"{star}<b>{dtxt}</b> — {html.escape(title)}\n   {html.escape(', '.join(names))}")
        ids_labels.append((r.id, f"{dtxt} {title}"[:30], 0))
    text = "\n".join(lines)
    kb = history_kb(lang, faved, ids_labels)
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "history")
async def cb_history(callback: CallbackQuery, cfg: Config, analytics: Analytics) -> None:
    user = await get_or_create_user(callback.from_user, cfg)
    await analytics.track(user.id, "history_opened")
    await _render_history(callback.message, user)
    await callback.answer()


@router.callback_query(F.data.startswith("fav:"))
async def cb_fav(callback: CallbackQuery, cfg: Config) -> None:
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    parts = callback.data.split(":")
    try:
        reading_id = int(parts[1])
    except (ValueError, IndexError):
        await callback.answer("?")
        return
    from_history = len(parts) > 2 and parts[2] == "h"
    async with get_session() as session:
        reading = await session.get(Reading, reading_id)
    if reading is None or reading.user_id != user.id:
        await callback.answer("?")
        return
    now_faved = await _toggle_favorite(user.id, reading_id)
    if from_history:
        await _render_history(callback.message, user, edit=True)
        await callback.answer(t(lang, "fav_added") if now_faved else t(lang, "fav_removed"))
        return
    try:
        await callback.message.edit_reply_markup(
            reply_markup=(await _footer_kb_after_fav(lang, reading_id, now_faved))
        )
    except Exception:  # noqa: BLE001
        pass
    await callback.answer(t(lang, "fav_added") if now_faved else t(lang, "fav_removed"))


async def _footer_kb_after_fav(lang: str, reading_id: int, faved: bool):
    from ..keyboards import reading_footer_kb

    return reading_footer_kb(lang, reading_id, faved=faved)


def _top_cards_of_week(readings: list[Reading], lang: str, top_n: int = 3) -> list[str]:
    counts: dict[str, int] = {}
    for r in readings:
        for card, _rev in cards_from_codes(r.cards_json.split(",")):
            name = card.name(lang)
            counts[name] = counts.get(name, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return [name for name, _c in ranked[:top_n]]


async def send_weekly_mirror(bot: Bot, cfg: Config, user: User, session, week_str: str, analytics: Analytics) -> bool:
    """Weekly 'Mirror': aggregated cards + reflection. Returns True when sent."""
    lang = user.language
    if user.last_mirror_week == week_str:
        return False
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = (
        (
            await session.execute(
                select(Reading)
                .where(Reading.user_id == user.id, Reading.created_at >= since)
                .order_by(Reading.id.desc())
            )
        )
        .scalars()
        .all()
    )
    if len(rows) < 3:
        return False
    top = _top_cards_of_week(rows, lang)
    text = await weekly_mirror_text(cfg, lang, top, len(rows))
    if not text:
        cards_line = ", ".join(top) if top else "—"
        question = MIRROR_QUESTIONS[lang][secrets.randbelow(len(MIRROR_QUESTIONS[lang]))]
        text = (
            ("За неделю чаще всего тебе выпадали: " if lang == "ru" else "Your most frequent cards this week: ")
            + cards_line
            + f"\n\n✦ {question}"
        )
    await bot.send_message(user.id, f"<b>{t(lang, 'mirror_title')}</b>\n\n{text}", reply_markup=mirror_kb(lang))
    user.last_mirror_week = week_str
    await analytics.track(user.id, "mirror_sent", readings=len(rows))
    return True
