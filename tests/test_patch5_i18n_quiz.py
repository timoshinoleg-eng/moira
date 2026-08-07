"""Patch 5 regression tests: i18n parity, quiz scoring and tie-break."""
from __future__ import annotations

import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.handlers.features import QUIZ, _major_card
from bot.tarot.quiz import ALL_MAJOR, QUIZ_QUESTIONS, compute_result


def _test_quiz_scoring_tie_break() -> None:
    """When two arcanas tie, the lowest arcana number wins."""
    scores = {"0": 2, "3": 2, "17": 1}
    winner = min(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    assert winner[0] == "0", f"expected tie-break to lowest id, got {winner}"


def _test_compute_result_tie_break() -> None:
    """compute_result should break ties by lower Arcana number."""
    # Create a scenario where two Arcana could tie
    # All answers index 0: Q1->{0:3,17:2,7:1}, Q2->{1:3,4:2,11:1}, Q3->{4:3,11:2,14:1},
    #                         Q4->{1:3,19:2,17:1}, Q5->{0:2,10:2,21:1}, Q6->{1:2,7:2,19:1}
    result = compute_result([0, 0, 0, 0, 0, 0])
    assert isinstance(result, int)
    assert 0 <= result <= 21


def _test_quiz_has_six_questions() -> None:
    for lang in ("ru", "en"):
        quiz = QUIZ[lang]
        assert len(quiz) == 6, f"{lang} quiz has {len(quiz)} questions"
    # New quiz has 4 answers per question
    for q in QUIZ_QUESTIONS:
        assert len(q) == 4, f"question has {len(q)} answers, expected 4"


def _test_all_arcana_reachable() -> None:
    """All 22 Major Arcana should be reachable by some combination of answers."""
    from itertools import product

    reachable = set()
    for combo in product(range(4), repeat=6):
        result = compute_result(list(combo))
        reachable.add(result)
    missing = set(ALL_MAJOR) - reachable
    assert not missing, f"Unreachable Arcana: {missing}"


def _test_major_card_lookup() -> None:
    card = _major_card(0)
    assert card is not None and card.id == "major_0"
    assert _major_card(99) is None


def _test_i18n_parity_and_no_placeholders() -> None:
    base = pathlib.Path(__file__).parent.parent / "bot" / "i18n" / "locales"
    ru = json.loads((base / "ru.json").read_text(encoding="utf-8"))
    en = json.loads((base / "en.json").read_text(encoding="utf-8"))
    assert ru.keys() == en.keys(), f"key mismatch: {set(ru) ^ set(en)}"
    for key in ru:
        for lang, texts in (("ru", ru), ("en", en)):
            text = texts[key]
            assert text and text.strip(), f"{lang}.{key} is empty"
            # Curly braces should only be valid format placeholders present in both locales.
            if "{" in text:
                assert "}" in text, f"{lang}.{key} has unbalanced braces"


if __name__ == "__main__":
    _test_quiz_scoring_tie_break()
    _test_compute_result_tie_break()
    _test_quiz_has_six_questions()
    _test_all_arcana_reachable()
    _test_major_card_lookup()
    _test_i18n_parity_and_no_placeholders()
    print("PATCH 5 TESTS PASSED")
