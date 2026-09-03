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


def invite_menu_kb(lang: str, share_url: str = "") -> InlineKeyboardMarkup:
    rows = []
    if share_url:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_invite_share"), url=share_url)])
    rows.extend(
        [
            [InlineKeyboardButton(text=t(lang, "btn_tariffs"), callback_data="tariffs")],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)

def reading_footer_kb(
    lang: str, reading_id: int, spread_id: str = "", faved: bool = False
) -> InlineKeyboardMarkup:
    fav_text = t(lang, "btn_unfav") if faved else t(lang, "btn_fav")
    followup_buttons = _followup_buttons(lang, reading_id, spread_id)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_share"), callback_data=f"share:{reading_id}"),
                InlineKeyboardButton(text=fav_text, callback_data=f"fav:{reading_id}"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_feedback_yes"), callback_data=f"feedback:{reading_id}:yes"),
                InlineKeyboardButton(text=t(lang, "btn_feedback_no"), callback_data=f"feedback:{reading_id}:no"),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_note"), callback_data=f"note:{reading_id}")],
            followup_buttons,
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")],
        ]
    )


def note_card_kb(lang: str, reading_id: int) -> InlineKeyboardMarkup:
    """View/edit/delete controls for one reading note."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "btn_note_edit"), callback_data=f"note_edit:{reading_id}"),
                InlineKeyboardButton(text=t(lang, "btn_note_delete"), callback_data=f"note_del:{reading_id}"),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")],
        ]
    )


def _followup_buttons(lang: str, reading_id: int, spread_id: str) -> list[InlineKeyboardButton]:
    followups = {
        "situation": [("hidden", "btn_follow_hidden"), ("next", "btn_follow_next")],
        "love": [("hidden", "btn_follow_dynamic"), ("next", "btn_follow_focus")],
        "choice": [("hidden", "btn_follow_compare"), ("next", "btn_follow_criterion")],
    }.get(spread_id, [("deeper", "btn_follow_deeper")])
    return [
        InlineKeyboardButton(text=t(lang, key), callback_data=f"follow:{reading_id}:{kind}")
        for kind, key in followups
    ]


def feedback_reengagement_kb(lang: str, reading_id: int, spread_id: str) -> InlineKeyboardMarkup:
    """Offer the most relevant next action immediately after feedback."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _followup_buttons(lang, reading_id, spread_id),
            [InlineKeyboardButton(text=t(lang, "btn_share"), callback_data=f"share:{reading_id}")],
            [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")],
        ]
    )


def history_kb(lang: str, readings_ids: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """readings_ids: [(reading_id, short_label)] — opens a complete saved reading."""
    rows = []
    for rid, label in readings_ids:
        rows.append([InlineKeyboardButton(text=label, callback_data=f"history:open:{rid}")])
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


def question_input_kb(
    lang: str, spread_id: str, *, voice_enabled: bool = False
) -> InlineKeyboardMarkup:
    rows = []
    if voice_enabled:
        rows.append(
            [InlineKeyboardButton(text=t(lang, "btn_voice_question"), callback_data=f"voice:start:{spread_id}")]
        )
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu")])
    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def voice_consent_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_voice_consent"), callback_data="voice:consent:yes")],
            [InlineKeyboardButton(text=t(lang, "btn_text_instead"), callback_data="voice:cancel")],
        ]
    )


def voice_waiting_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "btn_voice_cancel"), callback_data="voice:cancel")]]
    )


def voice_transcript_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_voice_confirm"), callback_data="voice:confirm")],
            [
                InlineKeyboardButton(text=t(lang, "btn_voice_edit"), callback_data="voice:edit"),
                InlineKeyboardButton(text=t(lang, "btn_voice_repeat"), callback_data="voice:repeat"),
            ],
            [InlineKeyboardButton(text=t(lang, "btn_voice_cancel"), callback_data="voice:cancel")],
        ]
    )
