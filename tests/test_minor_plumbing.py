"""QW-2 plumbing: per-card minor keywords/symbols with suit fallback.

The S1/S2 content drop has landed (56 symbols + 56 keyword sets), so the real
content is exercised here. These tests pin: card-specific keywords instead of the
old suit-level defaults, per-card override over the suit fallback, and the data-bug
class (latin inside RU fields). test_minor_content.py below runs the full
scripts/validate_minor_content.py acceptance checks.
"""
from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot.tarot.deck as deck_module
from bot.tarot.data_minor import SUITS
from bot.tarot.deck import build_deck, deck_index


def _minors() -> list:
    deck_module._DECK_INDEX = None
    return [c for c in build_deck() if c.arcana == "minor"]


def test_minor_keywords_are_card_specific() -> None:
    """S2 fixed the suit-level collapse: 56 cards no longer share 4 keyword sets."""
    cards = _minors()
    assert len(cards) == 56
    for card in cards:
        assert len(card.keywords_ru) == 3 and all(card.keywords_ru)
        assert len(card.keywords_en) == 3 and all(card.keywords_en)
        # The bug this content drop removes: every minor card carried the suit theme.
        assert card.keywords_ru != SUITS[card.suit]["kw_ru"], card.id
        assert card.keywords_en != SUITS[card.suit]["kw_en"], card.id
    # All 56 sets distinct per language — no two cards read the same in a prompt.
    assert len({tuple(c.keywords_ru) for c in cards}) == 56
    assert len({tuple(c.keywords_en) for c in cards}) == 56


def test_per_card_override_beats_suit_fallback(monkeypatch) -> None:
    import bot.tarot.deck as dm

    monkeypatch.setattr(dm, "MINOR_KEYWORDS", {
        "wands_ace": {"kw_ru": ["искра", "старт", "смелость"], "kw_en": ["spark", "beginning", "boldness"]},
    })
    monkeypatch.setattr(dm, "MINOR_SYMBOLS", {
        "wands_ace": {"ru": ["рука из облака", "прорастающий жезл", "дальний замок"],
                      "en": ["hand from a cloud", "sprouting wand", "distant castle"]},
    })
    monkeypatch.setattr(dm, "_DECK_INDEX", None)
    index = deck_module.deck_index()
    ace = index["wands_ace"]
    ten = index["wands_ten"]
    assert ace.keywords_ru == ["искра", "старт", "смелость"]
    assert ace.keywords_ru != ten.keywords_ru
    assert ten.keywords_ru == SUITS["wands"]["kw_ru"]
    assert ace.ru.symbols == ["рука из облака", "прорастающий жезл", "дальний замок"]
    assert ace.ru.symbols != ten.ru.symbols
    monkeypatch.setattr(dm, "_DECK_INDEX", None)


def test_major_symbols_present_both_langs() -> None:
    deck_module._DECK_INDEX = None
    majors = [c for c in build_deck() if c.arcana == "major"]
    assert len(majors) == 22
    for card in majors:
        assert len(card.ru.symbols) >= 3, card.id
        assert len(card.en.symbols) >= 3, card.id


def test_no_latin_in_ru_fields() -> None:
    deck_module._DECK_INDEX = None
    latin = re.compile(r"[A-Za-z]")
    for card in build_deck():
        for token in list(card.keywords_ru) + list(card.ru.symbols):
            assert not latin.search(token), f"{card.id}: {token!r}"


def test_build_card_block_snapshot() -> None:
    from bot.llm.adapter import _build_card_block
    from bot.tarot.spreads import DrawnCard

    deck_module._DECK_INDEX = None
    index = deck_index()
    drawn = DrawnCard(
        position_id="you",
        position_label={"ru": "Твоё состояние", "en": "Your state"},
        card=index["major_6"],
        reversed=False,
    )
    block = _build_card_block("ru", drawn, "love")
    assert block == (
        "Позиция «Твоё состояние» (значение: состояние, потребности и вклад пользователя "
        "в отношения). Карта: Влюблённые (прямая). Ключевые темы: любовь, выбор, союз. "
        "Визуальные символы карты: архангел рафаил, дерево огня, дерево познания. "
        "Дар: Согласованность чувств, ценностей и выбора делает союз честнее, а решение устойчивее.. "
        "Тень: Сильное притяжение может скрыть идеализацию, зависимость или отказ сделать выбор.. "
        "Действие: Назови три главные ценности и выбери действие, которое не противоречит ни одной из них.."
    )


def test_minor_content_acceptance_when_drop_lands() -> None:
    """Full A4 acceptance checks. Skips only if the content drop is ever reverted."""
    from bot.tarot.data_minor import MINOR_KEYWORDS
    from bot.tarot.data_symbols import MINOR_SYMBOLS

    if not MINOR_KEYWORDS or not MINOR_SYMBOLS:
        pytest.skip("S1/S2 content not delivered yet")
    from pathlib import Path

    scripts_dir = str(Path(__file__).resolve().parents[1] / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from validate_minor_content import validate

    assert validate() == []
    deck_module._DECK_INDEX = None
    index = deck_index()
    minors = [c for c in index.values() if c.arcana == "minor"]
    assert len(minors) == 56
    for card in minors:
        assert len(card.keywords("ru")) == 3
        assert len(card.keywords("en")) == 3
        assert card.ru.symbols and card.en.symbols
    assert index["wands_ace"].keywords_ru != index["wands_ten"].keywords_ru
