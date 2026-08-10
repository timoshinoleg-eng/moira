"""Launch-visible regressions for Journal, feedback, follow-up and LLM context."""
from __future__ import annotations

import json
from pathlib import Path

from bot.keyboards import history_kb, reading_footer_kb
from bot.llm.adapter import _build_user_message
from bot.tarot import draw


ROOT = Path(__file__).resolve().parents[1]


def _callbacks(keyboard) -> set[str]:
    return {
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data
    }


def test_followup_and_feedback_actions_are_contextual_and_localised() -> None:
    situation = _callbacks(reading_footer_kb("ru", 42, "situation"))
    choice = _callbacks(reading_footer_kb("en", 42, "choice"))
    assert {"follow:42:hidden", "follow:42:next", "feedback:42:yes", "feedback:42:no"} <= situation
    assert {"follow:42:hidden", "follow:42:next", "feedback:42:yes", "feedback:42:no"} <= choice


def test_history_entries_open_the_saved_reading_not_only_favourite_it() -> None:
    callbacks = _callbacks(history_kb("en", [(7, "08.10 Situation")]))
    assert "history:open:7" in callbacks
    assert not any(callback.startswith("fav:") for callback in callbacks)


def test_llm_message_keeps_each_spreads_position_without_global_state() -> None:
    situation = draw("situation")
    choice = draw("choice")
    situation_message = _build_user_message("en", "situation", "Situation", "How should I proceed?", situation, "")
    choice_message = _build_user_message("en", "choice", "Choice", "A or B?", choice, "")
    assert "what is happening now" in situation_message
    assert "potential, opportunities, and cost of the first path" in choice_message


def test_new_product_copy_has_ru_en_parity() -> None:
    ru = json.loads((ROOT / "bot" / "i18n" / "locales" / "ru.json").read_text(encoding="utf-8"))
    en = json.loads((ROOT / "bot" / "i18n" / "locales" / "en.json").read_text(encoding="utf-8"))
    keys = {
        "ask_question_situation",
        "ask_question_love",
        "ask_question_choice",
        "btn_feedback_yes",
        "btn_feedback_no",
        "feedback_thanks",
        "btn_follow_hidden",
        "btn_follow_next",
        "btn_follow_dynamic",
        "btn_follow_focus",
        "btn_follow_compare",
        "btn_follow_criterion",
        "btn_follow_deeper",
        "history_question",
        "history_general_reading",
        "history_cards",
        "history_interpretation_unavailable",
        "share_summary_legacy",
    }
    assert keys <= ru.keys()
    assert keys <= en.keys()
