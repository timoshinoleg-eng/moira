"""Tests for deterministic fallback composer."""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.tarot import draw
from bot.tarot.fallback import compose_fallback_reading


def test_fallback_has_all_fields() -> None:
    for spread_id in ("situation", "love", "choice"):
        drawn = draw(spread_id)
        for lang in ("ru", "en"):
            result = compose_fallback_reading(lang, spread_id, drawn)
            assert result["headline"], f"{spread_id} {lang}: missing headline"
            assert result["card_texts"], f"{spread_id} {lang}: missing card_texts"
            assert result["synthesis"], f"{spread_id} {lang}: missing synthesis"
            assert result["practical_focus"], f"{spread_id} {lang}: missing practical_focus"
            assert result["reflection_question"], f"{spread_id} {lang}: missing reflection_question"
            assert result["voice_text"], f"{spread_id} {lang}: missing voice_text"
            assert result["plain_text"], f"{spread_id} {lang}: missing plain_text"


def test_fallback_card_count_matches() -> None:
    for spread_id in ("situation", "love", "choice"):
        drawn = draw(spread_id)
        result = compose_fallback_reading("ru", spread_id, drawn)
        assert len(result["card_texts"]) == len(drawn), (
            f"{spread_id}: card_texts count mismatch"
        )


def test_fallback_contains_position_labels() -> None:
    drawn = draw("situation")
    result = compose_fallback_reading("ru", "situation", drawn)
    for d in drawn:
        label = d.position_label["ru"]
        found = any(label in ct for ct in result["card_texts"])
        assert found, f"Position label '{label}' not found in card_texts"


def test_fallback_synthesis_differs_by_spread() -> None:
    syntheses = {}
    for spread_id in ("situation", "love", "choice"):
        drawn = draw(spread_id)
        result = compose_fallback_reading("ru", spread_id, drawn)
        syntheses[spread_id] = result["synthesis"]
    # Each spread should have a distinct synthesis
    assert syntheses["situation"] != syntheses["love"]
    assert syntheses["love"] != syntheses["choice"]
    assert syntheses["situation"] != syntheses["choice"]


def test_fallback_no_false_personalization() -> None:
    """Fallback should not invent personal details."""
    drawn = draw("love")
    result = compose_fallback_reading("en", "love", drawn)
    text = result["plain_text"] + result["synthesis"]
    # Should not claim to know another person's thoughts as fact
    assert "he thinks" not in text.lower()
    assert "she thinks" not in text.lower()
    assert "he feels" not in text.lower()
    assert "she feels" not in text.lower()


def test_fallback_ru_en_parity() -> None:
    """RU and EN versions should have the same structure."""
    drawn = draw("situation")
    ru = compose_fallback_reading("ru", "situation", drawn)
    en = compose_fallback_reading("en", "situation", drawn)
    assert len(ru["card_texts"]) == len(en["card_texts"])
    assert bool(ru["synthesis"]) == bool(en["synthesis"])
    assert bool(ru["practical_focus"]) == bool(en["practical_focus"])


def test_fallback_pattern_detection() -> None:
    """Pattern detection should not crash and return a string."""
    from bot.tarot.fallback import _detect_pattern, _detect_pattern_en
    drawn = draw("choice")
    pattern_ru = _detect_pattern(drawn)
    pattern_en = _detect_pattern_en(drawn)
    assert isinstance(pattern_ru, str)
    assert isinstance(pattern_en, str)


def run_all() -> None:
    tests = [
        test_fallback_has_all_fields,
        test_fallback_card_count_matches,
        test_fallback_contains_position_labels,
        test_fallback_synthesis_differs_by_spread,
        test_fallback_no_false_personalization,
        test_fallback_ru_en_parity,
        test_fallback_pattern_detection,
    ]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print("\nALL FALLBACK TESTS PASSED")


if __name__ == "__main__":
    run_all()
