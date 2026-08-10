"""Regression tests for the share-caption experiment and return loop."""
from __future__ import annotations

import json
from pathlib import Path

from bot.handlers.helpers import parse_referral_attribution, parse_referral_param
from bot.handlers.reading import _share_caption_key, _share_referral_link, share_caption_variant
from bot.keyboards import feedback_reengagement_kb


ROOT = Path(__file__).resolve().parents[1]


def _callbacks(keyboard) -> set[str]:
    return {
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data
    }


def test_share_variant_is_stable_and_referral_link_carries_it() -> None:
    variant = share_caption_variant(42)
    assert variant in {"a", "b"}
    assert share_caption_variant(42) == variant
    assert _share_referral_link("moira_bot", 42, variant).endswith(f"ref_42_{variant}")
    assert _share_caption_key("voice", variant) == f"share_caption_voice_{variant}"
    assert _share_caption_key("text", variant) == f"share_caption_{variant}"


def test_referral_attribution_is_backward_compatible_and_rejects_bad_links() -> None:
    assert parse_referral_attribution("ref_123_a", 456) == (123, "a")
    assert parse_referral_attribution("ref_123", 456) == (123, None)
    assert parse_referral_param("ref_123_b", 456) == 123
    assert parse_referral_attribution("ref_123_c", 456) is None
    assert parse_referral_attribution("ref_456_a", 456) is None
    assert parse_referral_attribution("ref_0_a", 456) is None


def test_feedback_opens_contextual_return_loop() -> None:
    callbacks = _callbacks(feedback_reengagement_kb("ru", 42, "situation"))
    assert {"follow:42:hidden", "follow:42:next", "share:42", "menu"} <= callbacks


def test_growth_copy_has_ru_en_parity() -> None:
    ru = json.loads((ROOT / "bot" / "i18n" / "locales" / "ru.json").read_text(encoding="utf-8"))
    en = json.loads((ROOT / "bot" / "i18n" / "locales" / "en.json").read_text(encoding="utf-8"))
    keys = {
        "feedback_next_positive",
        "feedback_next_negative",
        "share_caption_a",
        "share_caption_b",
        "share_caption_voice_a",
        "share_caption_voice_b",
        "question_text_only",
    }
    assert keys <= ru.keys()
    assert keys <= en.keys()
    assert "{link}" in ru["share_caption_a"]
    assert "{link}" in en["share_caption_b"]
