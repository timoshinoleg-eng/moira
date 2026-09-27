from __future__ import annotations

import logging
from datetime import date, datetime

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_calendar import SimpleCalendar
from aiogram_calendar.schemas import CalendarLabels, SimpleCalAct

from .i18n import t

logger = logging.getLogger(__name__)

# Nobody alive was born before 1900, and a birth date in the future is
# meaningless. The calendar greys those days out, but we re-check the value
# server-side: callback data is fully client-controlled, and a hand-crafted
# `simple_calendar:DAY:3000:1:1` would otherwise be stored as the user's birth
# date and quietly poison every sun-sign calculation downstream.
MIN_BIRTH = date(1900, 1, 1)

MANUAL_CALLBACK = "birth:manual"

# Three-letter abbreviations keep the grid narrow enough for a phone. Russian uses
# the lowercase short forms Telegram's own date picker shows.
_MONTHS = {
    "ru": ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}
_WEEKDAYS = {
    "ru": ["пн", "вт", "ср", "чт", "пт", "сб", "вс"],
    "en": ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
}


def base_lang(lang: str) -> str:
    """Mirror the fallback in i18n.core.t: anything unknown is served in Russian."""
    return lang if lang in _MONTHS else "ru"


def is_plausible_birth(value: date) -> bool:
    return MIN_BIRTH <= value <= date.today()


def _calendar(lang: str) -> SimpleCalendar:
    base = base_lang(lang)
    cal = SimpleCalendar(cancel_btn=t(base, "cal_cancel"), today_btn=t(base, "cal_today"))
    # The library localises month/weekday names only through the stdlib locale
    # database (`SimpleCalendar(locale=...)`), which the slim Docker image does
    # not ship and which resolves differently on Windows and Linux. Assigning the
    # labels keeps the calendar identical on every platform. It is a private
    # attribute, so the guard matters: if a future major version renames it we
    # fall back to the library's English defaults instead of raising.
    labels: CalendarLabels | None = getattr(cal, "_labels", None)
    if labels is None:
        logger.warning("aiogram-calendar label API changed; month names stay English")
    else:
        labels.days_of_week = list(_WEEKDAYS[base])
        labels.months = list(_MONTHS[base])
    # start_calendar() only draws; process_day_select() enforces the same range,
    # so the widget and the save path agree on what is selectable.
    cal.set_dates_range(datetime(MIN_BIRTH.year, 1, 1), datetime.now())
    return cal


async def birth_calendar_kb(lang: str) -> InlineKeyboardMarkup:
    """The birth-date grid with a manual-entry escape hatch.

    Typing `07.03.1995` still works, but a grid is the only sane way to enter a
    date on a phone. The manual button is appended rather than offered first:
    picking a birthday is the common case, and an on-screen keyboard covering
    half the display is exactly what the grid exists to avoid.
    """
    base = base_lang(lang)
    today = date.today()
    kb = await _calendar(base).start_calendar(today.year, today.month)
    kb.inline_keyboard.append(
        [InlineKeyboardButton(text=t(base, "birth_manual"), callback_data=MANUAL_CALLBACK)]
    )
    return kb


async def process_birth_calendar(
    callback: CallbackQuery, data, lang: str
) -> date | None:
    """Drive one calendar tap.

    Returns the chosen date, or None when the tap was navigation, today, cancel,
    an out-of-range day, or a padding cell. Three library quirks are handled here:

    - `_update_calendar` and a successful day tap never call `query.answer()`, so
      the client would keep spinning the button until the 30s timeout. We answer
      on every path the library leaves unanswered.
    - `process_selection` *does* answer for the padding `IGNORE` action and for a
      rejected out-of-range day, and answering twice raises `TelegramBadRequest`
      ("query is too old"). Hence the act check, with the swallowed exception as a
      second line of defence.
    """
    picked, value = await _calendar(base_lang(lang)).process_selection(callback, data)
    if not picked:
        if data.act != SimpleCalAct.ignore:
            try:
                await callback.answer()
            except TelegramBadRequest:
                pass
        return None
    # A chosen day: the library deleted the grid but never answered the query.
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass
    # The library hands back a datetime; the rest of the codebase stores ISO dates.
    return value.date() if isinstance(value, datetime) else value
