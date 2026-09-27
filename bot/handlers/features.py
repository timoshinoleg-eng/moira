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
from aiogram_calendar import SimpleCalendarCallback
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
from ..astro.sky import safe_altar_lines
from ..config import Config
from ..datepicker import (
    MANUAL_CALLBACK,
    birth_calendar_kb,
    is_plausible_birth,
    process_birth_calendar,
)
from ..db.database import get_session
from ..db.models import Reading, ReadingFavorite, User
from ..i18n import t
from ..keyboards import altar_kb, back_menu_kb, history_kb, main_menu_kb, mirror_kb
from ..llm.adapter import weekly_mirror_text
from ..services.analytics import Analytics
from ..services.streaks import streak_line, track_ritual
from ..tarot import SPREADS
from ..tarot.deck import build_deck, cards_from_codes
from ..visual.render import make_single_image
from .helpers import ensure_utc, get_or_create_user, referral_link

logger = logging.getLogger(__name__)
router = Router()

BIRTH_RE = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s*$")

from ..tarot.quiz import (
    QUIZ_QUESTIONS,
    compute_result,
    format_arcana_result,
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


async def _save_birth(bot: Bot, chat_id: int, user: User, birth: date, cfg: Config) -> bool:
    """Persist a birth date and reveal the altar. Returns False if it was rejected.

    Shared by the calendar and the typed path so both validate identically: the
    grid greys impossible days out, but typed input and crafted callback data
    both need the same range check before anything is written to the database.
    """
    lang = user.language
    if not is_plausible_birth(birth):
        await bot.send_message(chat_id, t(lang, "birth_out_of_range"))
        return False
    async with get_session() as session:
        u = await session.get(User, user.id)
        u.birth_date = birth.isoformat()
        await session.commit()
        await session.refresh(u)
    await bot.send_message(chat_id, t(lang, "birth_ok"))
    await _show_altar(bot, chat_id, u, cfg)
    return True


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
    # The Moon's distance, true illuminated fraction and any quarter or perigee
    # landing tonight. Optional: safe_altar_lines cannot raise.
    lines.extend(safe_altar_lines(lang, today))

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
        # Show the grid instead of only asking for text. The state stays set, so a
        # user who dismisses the calendar can still type the date.
        await state.set_state(FeatureStates.waiting_birth)
        await callback.message.answer(
            t(lang, "birth_pick"),
            reply_markup=await birth_calendar_kb(lang),
        )
        await callback.answer()
        return
    # Opening the altar is a ritual visit in its own right, so it counts even
    # without a paid reading.
    await track_ritual(user.id, "altar")
    await _show_altar(callback.bot, callback.message.chat.id, user, cfg)
    await callback.answer()


@router.callback_query(F.data == "altar:set_birth")
async def cb_altar_set_birth(callback: CallbackQuery, state: FSMContext, cfg: Config) -> None:
    # This button has been on the altar screen since it was added, with no
    # handler behind it: tapping "Set birth date" did nothing at all. Reached
    # only by users who already have a date, so overwriting is the point.
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    await state.set_state(FeatureStates.waiting_birth)
    await callback.message.answer(
        t(lang, "birth_pick"),
        reply_markup=await birth_calendar_kb(lang),
    )
    await callback.answer()


@router.callback_query(SimpleCalendarCallback.filter())
async def cb_birth_calendar(
    callback: CallbackQuery,
    callback_data: SimpleCalendarCallback,
    state: FSMContext,
    cfg: Config,
) -> None:
    # Bound to the one shared `simple_calendar:` prefix. A second SimpleCalendar
    # elsewhere in the bot would need its own handler or this one eats its taps.
    user = await get_or_create_user(callback.from_user, cfg)
    # Navigating months must not leave the FSM armed: the typed handler would
    # then swallow whatever the user sends next.
    await state.clear()
    picked = await process_birth_calendar(callback, callback_data, user.language)
    if picked is None:
        return
    saved = await _save_birth(callback.bot, callback.message.chat.id, user, picked, cfg)
    if not saved:
        # The grid cannot produce such a date, so this is a rejected forged tap.
        # Re-offer the grid anyway so the "try again" reply has something to try.
        await state.set_state(FeatureStates.waiting_birth)
        await callback.message.answer(
            t(user.language, "birth_pick"),
            reply_markup=await birth_calendar_kb(user.language),
        )


@router.callback_query(F.data == MANUAL_CALLBACK)
async def cb_birth_manual(callback: CallbackQuery, state: FSMContext, cfg: Config) -> None:
    user = await get_or_create_user(callback.from_user, cfg)
    await state.set_state(FeatureStates.waiting_birth)
    await callback.message.answer(t(user.language, "birth_manual_hint"))
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
    await _save_birth(message.bot, message.chat.id, user, birth, cfg)


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

    # Finishing the quiz is a full ritual visit and the most shareable moment.
    ritual = await track_ritual(user.id, "quiz")
    title = t(lang, "quiz_result_title", name=arcana_name)
    if card is not None:
        # The arcana result is the most shareable artifact the bot produces, so it
        # carries its own invite QR: a screenshot of the banner becomes a signup.
        me = await callback.bot.me()
        invite_link = referral_link(me.username or "", user.id)
        photo = await asyncio.to_thread(
            make_single_image, title, result_text, card, footer="MOIRA ✦ TAROT", lang=lang,
            reversed_=False, qr_link=invite_link, qr_label=t(lang, "qr_invite_label_quiz"),
        )
        await callback.message.answer_photo(
            BufferedInputFile(photo, filename="arcana.jpg"),
            caption=f"<b>{title}</b>\n{result_text}",
        )
    else:
        await callback.message.answer(f"<b>{title}</b>\n{result_text}")
    share_text = t(lang, "quiz_share")
    if ritual is not None:
        share_text = f"{streak_line(lang, ritual)}\n\n{share_text}"
    await callback.message.answer(share_text, reply_markup=back_menu_kb(lang))
    await callback.answer()


async def send_daily_push(bot: Bot, cfg: Config, user: User, session, today_str: str) -> str | None:
    """Morning personal altar push.

    Returns ``None`` when the message went out, otherwise a short reason: the
    caller's job. The M-09 worker needs to tell "already sent today" and "the
    user blocked the bot" apart, because one is finished work and the other must
    not be retried. Returning a bare bool made both look like failure.
    """
    lang = user.language
    if not user.daily_push:
        return "opted_out"
    if user.last_push_date == today_str:
        return "already_sent"
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
        return classify_push_error(exc)
    user.last_push_date = today_str
    return None


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
        ids_labels.append((r.id, f"{star}{dtxt} {title}"[:46]))
    text = "\n".join(lines)
    kb = history_kb(lang, ids_labels)
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


@router.callback_query(F.data.startswith("history:open:"))
async def cb_history_open(callback: CallbackQuery, cfg: Config, analytics: Analytics) -> None:
    try:
        reading_id = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("?")
        return
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    async with get_session() as session:
        reading = await session.get(Reading, reading_id)
        faved = bool(
            await session.scalar(
                select(ReadingFavorite.id).where(
                    ReadingFavorite.user_id == user.id,
                    ReadingFavorite.reading_id == reading_id,
                )
            )
        )
    if reading is None or reading.user_id != user.id:
        await callback.answer(t(lang, "history_empty"))
        return
    title = SPREADS[reading.spread]["title"][lang] if reading.spread in SPREADS else reading.spread
    positions = SPREADS.get(reading.spread, {}).get("positions", [])
    card_lines = []
    for index, (card, reversed_) in enumerate(cards_from_codes(reading.cards_json.split(","))):
        label = positions[index][1].get(lang, positions[index][1]["ru"]) if index < len(positions) else str(index + 1)
        card_lines.append(
            f"• <i>{html.escape(label)}</i>: <b>{html.escape(card.name(lang))}</b>"
            + (t(lang, "rev_mark") if reversed_ else "")
        )
    question = reading.question or t(lang, "history_general_reading")
    interpretation = (reading.interpretation or t(lang, "history_interpretation_unavailable")).strip()
    header_text = "\n".join(
        [
            f"<b>{html.escape(title)}</b>",
            f"<i>{html.escape(t(lang, 'history_question', question=question))}</i>",
            f"<b>{t(lang, 'history_cards')}</b>",
            *card_lines,
        ]
    )
    from ..keyboards import reading_footer_kb

    # A reading can be 3,900 characters. Send its metadata separately so a
    # saved question plus three cards never pushes one Telegram message past
    # the 4,096-character limit.
    await callback.message.answer(header_text)
    await callback.message.answer(
        f"<b>{t(lang, 'spread_interpretation_header')}</b>\n{html.escape(interpretation)}",
        reply_markup=reading_footer_kb(lang, reading.id, reading.spread, faved=faved),
    )
    await analytics.track(user.id, "reading_reopened", reading_id=reading.id, spread=reading.spread)
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
    async with get_session() as session:
        reading = await session.get(Reading, reading_id)
    if reading is None or reading.user_id != user.id:
        await callback.answer("?")
        return
    now_faved = await _toggle_favorite(user.id, reading_id)
    try:
        await callback.message.edit_reply_markup(
            reply_markup=(await _footer_kb_after_fav(lang, reading_id, reading.spread, now_faved))
        )
    except Exception:  # noqa: BLE001
        pass
    await callback.answer(t(lang, "fav_added") if now_faved else t(lang, "fav_removed"))


async def _footer_kb_after_fav(lang: str, reading_id: int, spread_id: str, faved: bool):
    from ..keyboards import reading_footer_kb

    return reading_footer_kb(lang, reading_id, spread_id, faved=faved)


# Reasons that must never be retried: Telegram will keep rejecting them, so a
# retry only burns rate limit. Shared with the M-09 worker.
PUSH_TERMINAL_CODES = frozenset(
    {
        "bot_blocked_by_user",
        "user_is_deactivated",
        "chat_not_found",
        "bot_kicked_from_chat",
    }
)

# Reasons that mean "there was nothing to send" rather than "the send failed".
# The work is finished either way, so these close the row instead of retrying it.
PUSH_SKIP_CODES = frozenset({"already_sent", "opted_out", "too_few_readings"})


def classify_push_error(exc: Exception) -> str:
    """Map a Telegram send failure onto a short, safe reason code.

    Only the exception type name and a keyword scan of the message are used, so
    no user text ever reaches the ledger.
    """
    text = str(exc).lower()
    if "bot was blocked" in text or "bot_blocked" in text:
        return "bot_blocked_by_user"
    if "deactivated" in text:
        return "user_is_deactivated"
    if "chat not found" in text:
        return "chat_not_found"
    if "kicked" in text:
        return "bot_kicked_from_chat"
    if "flood" in text or "retry after" in text:
        return "flood"
    return type(exc).__name__[:32]


def _top_cards_of_week(readings: list[Reading], lang: str, top_n: int = 3) -> list[str]:
    counts: dict[str, int] = {}
    for r in readings:
        for card, _rev in cards_from_codes(r.cards_json.split(",")):
            name = card.name(lang)
            counts[name] = counts.get(name, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return [name for name, _c in ranked[:top_n]]


async def send_weekly_mirror(bot: Bot, cfg: Config, user: User, session, week_str: str, analytics: Analytics) -> str | None:
    """Weekly 'Mirror': aggregated cards + reflection.

    Same contract as :func:`send_daily_push` — ``None`` when sent, otherwise a
    short reason. A user with fewer than three readings this week is a
    deliberate no-op (``"too_few_readings"``), not a failure, and the worker must
    close that row rather than retry it.
    """
    lang = user.language
    if user.last_mirror_week == week_str:
        return "already_sent"
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
        return "too_few_readings"
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
    try:
        await bot.send_message(user.id, f"<b>{t(lang, 'mirror_title')}</b>\n\n{text}", reply_markup=mirror_kb(lang))
    except Exception as exc:  # noqa: BLE001
        logger.warning("weekly mirror to %s failed: %s", user.id, exc)
        return classify_push_error(exc)
    user.last_mirror_week = week_str
    await analytics.track(user.id, "mirror_sent", readings=len(rows))
    return None
