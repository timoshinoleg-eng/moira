from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .i18n import t


def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_situation"), callback_data="spread:situation")],
            [InlineKeyboardButton(text=t(lang, "btn_love"), callback_data="spread:love")],
            [InlineKeyboardButton(text=t(lang, "btn_choice"), callback_data="spread:choice")],
            [
                InlineKeyboardButton(text=t(lang, "btn_altar"), callback_data="altar"),
                InlineKeyboardButton(text=t(lang, "btn_quiz"), callback_data="quiz"),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_history"), callback_data="history")],
            [
                InlineKeyboardButton(text=t(lang, "btn_tariffs"), callback_data="tariffs"),
                InlineKeyboardButton(text=t(lang, "btn_invite"), callback_data="invite"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_promo"), callback_data="promo:start"),
                InlineKeyboardButton(text=t(lang, "btn_lang"), callback_data="lang:toggle"),
            ],
        ]
    )


def altar_kb(lang: str, push_on: bool) -> InlineKeyboardMarkup:
    push_text = t(lang, "btn_push_off") if push_on else t(lang, "btn_push_on")
    push_cb = "altar:push_off" if push_on else "altar:push_on"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=push_text, callback_data=push_cb)],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")],
        ]
    )


def set_birth_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_set_birth"), callback_data="altar:set_birth")],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")],
        ]
    )


def paywall_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "tariff_one"), callback_data="pay:reading_1")],
            [InlineKeyboardButton(text=t(lang, "tariff_week"), callback_data="pay:unlimited_7")],
            [InlineKeyboardButton(text=t(lang, "tariff_month"), callback_data="pay:unlimited_30")],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")],
        ]
    )


def tariffs_kb(lang: str) -> InlineKeyboardMarkup:
    back = t(lang, "btn_back")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "tariff_one"), callback_data="pay:reading_1")],
            [InlineKeyboardButton(text=t(lang, "tariff_week"), callback_data="pay:unlimited_7")],
            [InlineKeyboardButton(text=t(lang, "tariff_month"), callback_data="pay:unlimited_30")],
            [InlineKeyboardButton(text=back, callback_data="menu")],
        ]
    )


def invite_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_tariffs"), callback_data="tariffs")],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")],
        ]
    )


def reading_footer_kb(lang: str, reading_id: int, faved: bool = False) -> InlineKeyboardMarkup:
    fav_text = t(lang, "btn_unfav") if faved else t(lang, "btn_fav")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_share"), callback_data=f"share:{reading_id}"),
                InlineKeyboardButton(text=fav_text, callback_data=f"fav:{reading_id}"),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")],
        ]
    )


def history_kb(lang: str, faved_reading_ids: set[int], readings_ids: list[tuple[int, str, int]]) -> InlineKeyboardMarkup:
    """readings_ids: [(reading_id, short_label, index)] — toggle buttons for favorites."""
    rows = []
    for rid, label, _idx in readings_ids:
        text = ("⭐ " if rid in faved_reading_ids else "☆ ") + label
        rows.append([InlineKeyboardButton(text=text, callback_data=f"fav:{rid}:h")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def mirror_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_situation"), callback_data="spread:situation")],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")],
        ]
    )


def back_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")]]
    )
