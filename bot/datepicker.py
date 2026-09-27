from __future__ import annotations

import logging
from datetime import date, datetime

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
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
DECADES_CALLBACK = "birth:decades"
DECADE_PREFIX = "birth:decade:"
YEAR_PREFIX = "birth:year:"

# Reusing the library's own padding action gives us a working no-op button for
# the greyed-out years: it is answered by the existing calendar handler, so
# disabled cells need no extra plumbing.
NOOP_CALLBACK = SimpleCalendarCallback(act=SimpleCalAct.ignore).pack()

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


class _BirthCalendar(SimpleCalendar):
    """The library's grid, plus a way into the years and a way out of it.

    Two additions the stock widget does not have, and both have to be applied
    *inside* `start_calendar` rather than to the finished markup:

    - The header is `<< [year] >>`, where the arrows move one year per tap and the
      year caption is a dead `IGNORE` pad. Reaching 1995 from 2026 that way is 31
      taps, so the caption becomes the way in.
    - The manual-entry button has to survive a redraw.

    The library re-renders through `start_calendar` on every arrow tap, so
    decorating the markup once in the caller silently lost both buttons as soon as
    the user moved a month. Overriding the single choke point fixes that.
    """

    def __init__(self, *args, manual_label: str | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._manual_label = manual_label

    async def start_calendar(self, year=None, month=None) -> InlineKeyboardMarkup:
        today = date.today()
        year = today.year if year is None else int(year)
        month = today.month if month is None else int(month)
        kb = await super().start_calendar(year, month)
        header = kb.inline_keyboard[0] if kb.inline_keyboard else []
        if len(header) == 3:
            header[1] = InlineKeyboardButton(text=f"[{year}]", callback_data=DECADES_CALLBACK)
        else:
            logger.warning("aiogram-calendar header layout changed; year jump unavailable")
        if self._manual_label:
            kb.inline_keyboard.append(
                [InlineKeyboardButton(text=self._manual_label, callback_data=MANUAL_CALLBACK)]
            )
        return kb


def _calendar(lang: str) -> _BirthCalendar:
    base = base_lang(lang)
    cal = _BirthCalendar(
        cancel_btn=t(base, "cal_cancel"),
        today_btn=t(base, "cal_today"),
        manual_label=t(base, "birth_manual"),
    )
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


def _clamp_year(value: int) -> int | None:
    """Callback data is client-controlled, so the year jump is validated too."""
    if MIN_BIRTH.year <= value <= date.today().year:
        return value
    return None


async def birth_calendar_kb(lang: str, year: int | None = None) -> InlineKeyboardMarkup:
    """The birth-date grid with a manual-entry escape hatch.

    Typing `07.03.1995` still works, but a grid is the only sane way to enter a
    date on a phone. The manual button is appended rather than offered first:
    picking a birthday is the common case, and an on-screen keyboard covering
    half the display is exactly what the grid exists to avoid.
    """
    today = date.today()
    return await _calendar(base_lang(lang)).start_calendar(
        year or today.year, today.month
    )


def decade_menu_kb() -> InlineKeyboardMarkup:
    """Decades from this one back to 1900, four per row.

    A decade is picked with a single tap, so any year is two taps away instead of
    the thirty-odd the one-year arrows would need. Labels are bare years, which
    need no translation and read the same in both languages.
    """
    this_year = date.today().year
    decades = list(range((this_year // 10) * 10, MIN_BIRTH.year - 1, -10))
    rows = [
        [
            InlineKeyboardButton(text=str(d), callback_data=f"{DECADE_PREFIX}{d}")
            for d in decades[i : i + 4]
        ]
        for i in range(0, len(decades), 4)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def year_menu_kb(decade_start: int) -> InlineKeyboardMarkup:
    """The ten years of one decade, five per row, unreachable years greyed out."""
    cells: list[InlineKeyboardButton] = []
    for year in range(decade_start, decade_start + 10):
        if _clamp_year(year) is None:
            cells.append(InlineKeyboardButton(text="·", callback_data=NOOP_CALLBACK))
        else:
            cells.append(
                InlineKeyboardButton(text=str(year), callback_data=f"{YEAR_PREFIX}{year}")
            )
    return InlineKeyboardMarkup(
        inline_keyboard=[cells[:5], cells[5:]] if len(cells) == 10 else [cells]
    )


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
