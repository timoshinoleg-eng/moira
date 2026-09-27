"""Birth-date calendar: rendering, save path, and the bounds a crafted tap must not cross."""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys
from datetime import date, datetime, timedelta

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram_calendar import SimpleCalendarCallback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bot.datepicker import (  # noqa: E402
    MANUAL_CALLBACK,
    MIN_BIRTH,
    base_lang,
    birth_calendar_kb,
    is_plausible_birth,
    process_birth_calendar,
)
from bot.handlers.features import FeatureStates, _parse_birth_date  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


class _FakeMessage:
    def __init__(self) -> None:
        self.deleted_markup = False
        self.edits: list[object] = []

    async def delete_reply_markup(self) -> None:
        self.deleted_markup = True

    async def edit_reply_markup(self, reply_markup=None) -> None:
        self.edits.append(reply_markup)


class _FakeCallback:
    """Enough of a CallbackQuery for the library and for our own answer() calls.

    `answer()` raises on a second call, exactly as Telegram does: a callback query
    can only be answered once, and the retry fails with "query is too old". That
    turns a double-answer into a loud test failure instead of a silent count.
    """

    def __init__(self) -> None:
        self.message = _FakeMessage()
        self.answers = 0
        self.from_user = None

    async def answer(self, *args, **kwargs) -> None:
        if self.answers:
            raise TelegramBadRequest(method="answerCallbackQuery", message="query is too old")
        self.answers += 1


def _cb(year: int, month: int, day: int) -> SimpleCalendarCallback:
    return SimpleCalendarCallback.unpack(
        SimpleCalendarCallback(act="DAY", year=year, month=month, day=day).pack()
    )


def _labels(kb) -> list[list[str]]:
    return [[b.text for b in row] for row in kb.inline_keyboard]


def _callbacks(kb) -> list[str]:
    return [b.callback_data for row in kb.inline_keyboard for b in row if b.callback_data]


# --- rendering ---------------------------------------------------------------


def _locale(lang: str) -> dict:
    path = ROOT / "bot" / "i18n" / "locales" / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_calendar_offers_a_manual_escape_hatch(lang: str) -> None:
    kb = asyncio.run(birth_calendar_kb(lang))
    assert MANUAL_CALLBACK in _callbacks(kb)
    # The label is read back from the locale file rather than hardcoded here, so
    # this asserts the button really is the translated "type it manually" and a
    # mangled source encoding in this file cannot mask a wrong caption.
    assert _labels(kb)[-1][0] == _locale(lang)["birth_manual"]


def test_month_names_follow_the_user_language() -> None:
    ru = _labels(asyncio.run(birth_calendar_kb("ru")))
    en = _labels(asyncio.run(birth_calendar_kb("en")))
    # Header layout is << [year] >> then < [month] >
    assert ru[1][1].startswith("[")
    assert en[1][1].startswith("[")
    assert ru[1][1] != en[1][1], "month caption must not stay English for a Russian user"


def test_cancel_and_today_captions_are_localised() -> None:
    ru = [b for row in _labels(asyncio.run(birth_calendar_kb("ru"))) for b in row]
    en = [b for row in _labels(asyncio.run(birth_calendar_kb("en"))) for b in row]
    assert _locale("ru")["cal_cancel"] in ru
    assert _locale("en")["cal_cancel"] in en
    assert _locale("ru")["cal_cancel"] not in en


def test_unknown_language_falls_back_to_russian() -> None:
    assert base_lang("de") == "ru"
    assert base_lang("en") == "en"


# --- plausibility ------------------------------------------------------------


def test_plausible_birth_window() -> None:
    assert is_plausible_birth(MIN_BIRTH)
    assert is_plausible_birth(date(1995, 3, 7))
    assert is_plausible_birth(date.today())
    assert not is_plausible_birth(MIN_BIRTH - timedelta(days=1))
    assert not is_plausible_birth(date.today() + timedelta(days=1))
    assert not is_plausible_birth(date(3000, 1, 1))


def test_typed_path_now_rejects_nonsense_years() -> None:
    # The parser still yields a date object; the range check happens on save, so
    # both entry points agree on what is acceptable.
    assert _parse_birth_date("07.03.1995") == date(1995, 3, 7)
    assert _parse_birth_date("01.01.3000") == date(3000, 1, 1)
    assert not is_plausible_birth(_parse_birth_date("01.01.3000"))  # type: ignore[arg-type]


# --- the crafted-callback boundary ------------------------------------------


def test_a_crafted_out_of_range_tap_is_not_saved() -> None:
    """A hand-written callback must not reach the database.

    The grid greys impossible days out, but callback data is client-controlled.
    Without the server-side check, `simple_calendar:DAY:3000:1:1` would be stored
    as the birth date and every sun-sign calculation would be wrong forever.
    """
    callback = _FakeCallback()
    picked = asyncio.run(process_birth_calendar(callback, _cb(3000, 1, 1), "ru"))
    assert picked is None, "year 3000 must not come back as a selected date"
    assert not is_plausible_birth(date(3000, 1, 1))


def test_a_future_tap_is_not_saved() -> None:
    future = date.today() + timedelta(days=30)
    callback = _FakeCallback()
    picked = asyncio.run(
        process_birth_calendar(callback, _cb(future.year, future.month, future.day), "en")
    )
    assert picked is None


def test_a_valid_tap_returns_the_chosen_date() -> None:
    callback = _FakeCallback()
    picked = asyncio.run(process_birth_calendar(callback, _cb(1995, 3, 7), "ru"))
    assert picked == date(1995, 3, 7)
    assert isinstance(picked, date) and not isinstance(picked, datetime)
    # process_day_select deletes the grid, and never answers the query itself.
    assert callback.message.deleted_markup is True
    assert callback.answers == 1, "a successful tap must answer, or Telegram spins for 30s"


def test_navigation_answers_and_keeps_the_grid() -> None:
    callback = _FakeCallback()
    data = SimpleCalendarCallback.unpack(
        SimpleCalendarCallback(act="NEXT-MONTH", year=2026, month=9, day=1).pack()
    )
    picked = asyncio.run(process_birth_calendar(callback, data, "ru"))
    assert picked is None
    assert callback.message.edits, "month navigation should redraw the grid"
    assert callback.answers == 1, "navigation must answer too"


def test_padding_cell_is_answered_exactly_once() -> None:
    """The library answers IGNORE itself, so we must not answer a second time."""
    callback = _FakeCallback()

    class _Msg:
        async def edit_reply_markup(self, reply_markup=None):
            raise AssertionError("IGNORE must not touch the message")

    callback.message = _Msg()
    data = SimpleCalendarCallback.unpack(
        SimpleCalendarCallback(act="IGNORE", year=2026, month=9, day=1).pack()
    )
    picked = asyncio.run(process_birth_calendar(callback, data, "ru"))
    assert picked is None
    # The strict fake raises on a second answer, so reaching here means we stayed
    # quiet and the library's single answer stood.
    assert callback.answers == 1


# --- locale parity -----------------------------------------------------------


def test_new_keys_exist_in_both_locales() -> None:
    keys = {
        "cal_cancel",
        "cal_today",
        "birth_pick",
        "birth_manual",
        "birth_manual_hint",
        "birth_out_of_range",
    }
    base = ROOT / "bot" / "i18n" / "locales"
    for lang in ("ru", "en"):
        data = json.loads((base / f"{lang}.json").read_text(encoding="utf-8"))
        missing = keys - set(data)
        assert not missing, f"{lang} is missing {missing}"


def test_ru_and_en_stay_in_sync() -> None:
    base = ROOT / "bot" / "i18n" / "locales"
    ru = json.loads((base / "ru.json").read_text(encoding="utf-8"))
    en = json.loads((base / "en.json").read_text(encoding="utf-8"))
    assert set(ru) == set(en)


def test_birth_state_is_still_registered_for_the_typed_path() -> None:
    assert FeatureStates.waiting_birth.state


# --- persistence -------------------------------------------------------------


class _FakeBot:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_message(self, chat_id, text, **kwargs) -> None:
        self.sent.append(text)


def _run_save(tmp_path, db_user_id: int, birth: date):
    """Drive _save_birth against a throwaway SQLite database."""
    from bot.config import load_config
    from bot.db.database import close_db, get_session, init_db
    from bot.db.models import User as DbUser
    from bot.handlers import features as F

    async def main():
        await init_db(str(tmp_path / "birth.db"))
        try:
            async with get_session() as session:
                # User.id *is* the Telegram id, so it is set explicitly.
                row = DbUser(id=db_user_id, language="ru", first_name="T")
                session.add(row)
                await session.commit()
                await session.refresh(row)
                detached = DbUser(id=row.id, language=row.language, birth_date=None)

            shown: list[object] = []
            original = F._show_altar

            async def fake_show_altar(bot, chat_id, user, cfg):
                shown.append(user)

            F._show_altar = fake_show_altar
            bot = _FakeBot()
            try:
                saved = await F._save_birth(
                    bot, 1, detached, birth, load_config(require_token=False)
                )
            finally:
                F._show_altar = original

            async with get_session() as session:
                stored = await session.get(DbUser, detached.id)
                persisted = stored.birth_date
            return persisted, list(bot.sent), shown, saved
        finally:
            await close_db()

    return asyncio.run(main())


def test_a_valid_date_is_persisted_and_the_altar_opens(tmp_path) -> None:
    persisted, sent, shown, saved = _run_save(tmp_path, 555, date(1995, 3, 7))
    assert saved is True
    assert persisted == "1995-03-07"
    assert shown, "the altar should open once the date is saved"
    assert _locale("ru")["birth_ok"] in sent


def test_a_crafted_future_date_is_never_written(tmp_path) -> None:
    """The DB is the real boundary: a rejected date must leave the row untouched."""
    persisted, sent, shown, saved = _run_save(tmp_path, 556, date(3000, 1, 1))
    assert saved is False
    assert persisted is None, "an out-of-range birth date must not reach the database"
    assert not shown, "the altar must not open for a rejected date"
    assert _locale("ru")["birth_out_of_range"] in sent


def test_save_reports_rejection_to_the_caller() -> None:
    """The calendar handler re-offers the grid on rejection, so it needs the verdict."""
    from bot.config import load_config
    from bot.db.models import User as DbUser
    from bot.handlers import features as F

    async def main():
        bot = _FakeBot()

        async def never(*a, **k):
            raise AssertionError("altar must not open for a rejected date")

        original = F._show_altar
        F._show_altar = never
        try:
            return await F._save_birth(
                bot, 1, DbUser(id=1, language="ru"), date(3000, 1, 1),
                load_config(require_token=False),
            )
        finally:
            F._show_altar = original

    assert asyncio.run(main()) is False
