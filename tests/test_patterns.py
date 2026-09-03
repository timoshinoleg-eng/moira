"""QW-3: deterministic card-pattern analyzer, no LLM."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.tarot.deck import deck_index
from bot.tarot.patterns import analyze_patterns, format_pattern_block
from bot.tarot.spreads import DrawnCard, SPREADS


def _drawn_cards(spec: list[tuple[str, str, bool]], lang: str = "ru") -> list[DrawnCard]:
    index = deck_index()
    positions = SPREADS["situation"]["positions"]
    return [
        DrawnCard(position_id=positions[i][0], position_label=positions[i][1],
                  card=index[card_id], reversed=rev)
        for i, (card_id, _lang, rev) in enumerate(spec)
    ]


def test_deterministic_same_input_same_output() -> None:
    drawn = _drawn_cards([("major_0", "ru", False), ("wands_ace", "ru", True), ("cups_two", "ru", False)])
    first = analyze_patterns(drawn, "ru")
    second = analyze_patterns(drawn, "ru")
    assert first == second
    assert format_pattern_block(first, "ru") == format_pattern_block(second, "ru")


def test_dominant_suit_none_on_tie_present_on_lead() -> None:
    tie = _drawn_cards([("major_0", "ru", False), ("wands_ace", "ru", False), ("cups_two", "ru", False)])
    assert analyze_patterns(tie, "ru").dominant_suit is None
    lead = _drawn_cards([("wands_ace", "ru", False), ("wands_two", "ru", False), ("cups_two", "ru", False)])
    summary = analyze_patterns(lead, "ru")
    assert summary.dominant_suit == "wands"
    assert summary.suit_counts == {"cups": 1, "wands": 2}
    assert summary.reversed_count == 0
    assert summary.major_count == 0 and summary.minor_count == 3


def test_block_short_caveat_and_no_fateful_language() -> None:
    drawn = _drawn_cards([("major_0", "ru", False), ("wands_ace", "ru", True), ("wands_two", "ru", False)])
    block = format_pattern_block(analyze_patterns(drawn, "ru"), "ru")
    lines = block.splitlines()
    assert len(lines) <= 6
    assert "не выдумывай дополнительные паттерны" in lines[0]
    low = block.casefold()
    for banned in ("судьб", "неизбежн", "предсказан", "destiny", "fate", "нумеролог"):
        assert banned not in low
    assert "Преобладает: Жезлы." in block
    assert "Перевёрнутых карт: 1 из 3." in block


def test_shared_keyword_lines_render_pair_names() -> None:
    from types import SimpleNamespace

    def fake_card(name, keywords):
        return SimpleNamespace(arcana="minor", suit="wands",
                               name=lambda lang, n=name: n,
                               keywords=lambda lang, k=keywords: k)

    drawn = [
        SimpleNamespace(position_id="a", card=fake_card("Карта А", ["смелость", "старт"]), reversed=False),
        SimpleNamespace(position_id="b", card=fake_card("Карта Б", ["смелость", "риск"]), reversed=False),
        SimpleNamespace(position_id="c", card=fake_card("Карта В", ["покой"]), reversed=True),
    ]
    block = format_pattern_block(analyze_patterns(drawn, "ru"), "ru")
    assert "Общая тема «смелость»: Карта А и Карта Б." in block
    assert len(block.splitlines()) <= 6


def test_empty_draw_gives_empty_block() -> None:
    assert format_pattern_block(analyze_patterns([], "ru"), "ru") == ""


def test_prompt_regression_snapshot() -> None:
    from bot.llm.adapter import _build_user_message

    drawn = _drawn_cards([("major_0", "ru", False), ("wands_ace", "ru", True), ("cups_two", "ru", False)])
    message = _build_user_message("ru", "situation", "Расклад «Ситуация»", None, drawn, "")
    assert "Связи между картами: используй только как поддерживающий контекст, " in message
    block = format_pattern_block(analyze_patterns(drawn, "ru"), "ru")
    assert block in message
    assert block == (
        "Связи между картами: используй только как поддерживающий контекст, "
        "не выдумывай дополнительные паттерны.\n"
        "Старших Арканов: 1 из 3; младших: 2 из 3.\n"
        "Масти: Кубки 1, Жезлы 1.\n"
        "Перевёрнутых карт: 1 из 3."
    )
