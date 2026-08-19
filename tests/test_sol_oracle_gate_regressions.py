from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from bot.llm.adapter import _build_card_block
from bot.tarot.deck import build_deck
from bot.tarot.spreads import DrawnCard, SPREADS
from scripts.run_oracle_v6_eval import score_result


CYRILLIC_ORIENTATION_TOKENS = ("прямая", "перевёрнутая")


def _drawn(reversed_: bool, index: int = 0) -> DrawnCard:
    spread = SPREADS["situation"]
    position_id, labels = spread["positions"][index]
    return DrawnCard(
        position_id=position_id,
        position_label=labels,
        card=build_deck()[index],
        reversed=reversed_,
    )


def _clean_reading() -> dict:
    return {
        "headline": "A grounded threshold",
        "opening": "A threshold in this spread invites a calm look at what is changing without promising a fixed outcome.",
        "card_interpretations": [
            {
                "position": "Essence",
                "card_name": "The Fool",
                "orientation": "upright",
                "core_message": "The first card asks you to notice where curiosity can become a measured first step.",
                "symbolic_detail": "A road opens beyond the cliff.",
                "context_connection": "Let the next move remain yours rather than something decided by outside pressure.",
            },
            {
                "position": "Hidden factor",
                "card_name": "The Magician",
                "orientation": "upright",
                "core_message": "The second card highlights the resources already available when you name one practical priority.",
                "symbolic_detail": "Tools are placed clearly on the table.",
                "context_connection": "Choose one resource to test before asking the situation to reveal every answer at once.",
            },
            {
                "position": "Next step",
                "card_name": "The High Priestess",
                "orientation": "reversed",
                "core_message": "The final card suggests pausing long enough to separate a quiet intuition from a fear of uncertainty.",
                "symbolic_detail": "The curtain is partly drawn aside.",
                "context_connection": "Write down what you know and what you still need to observe before deciding.",
            },
        ],
        "synthesis": "Together the cards describe a road that becomes clearer through one modest experiment. Curiosity is useful, but the hidden factor is whether you use the tools already in your hands. A pause before the next step keeps intuition connected to what can actually be observed.",
        "practical_focus": "Choose one small action this week, then record what changed before committing to a larger decision.",
        "reflection_question": "What would become clearer if you treated the next step as an experiment rather than a final verdict?",
        "voice_summary": "You stand at a threshold where a small, conscious experiment can reveal more than a rushed answer. Use what is already available, keep the decision in your hands, and give yourself time to notice the difference between intuition and fear.",
        "share_summary": "A measured first step can make the road clearer while keeping the choice in your hands.",
    }


def _case(question: str = "What should I reflect on?") -> dict:
    return {"lang": "en", "question": question}


def test_ru_upright_card_block_uses_russian_orientation() -> None:
    block = _build_card_block("ru", _drawn(False), "situation")
    assert "прямая" in block


def test_ru_reversed_card_block_uses_russian_orientation() -> None:
    block = _build_card_block("ru", _drawn(True), "situation")
    assert "перевёрнутая" in block


def test_en_upright_card_block_uses_english_orientation_only() -> None:
    block = _build_card_block("en", _drawn(False), "situation")
    assert "upright" in block
    assert not any(token in block for token in CYRILLIC_ORIENTATION_TOKENS)


def test_en_reversed_card_block_uses_english_orientation_only() -> None:
    block = _build_card_block("en", _drawn(True), "situation")
    assert "reversed" in block
    assert not any(token in block for token in CYRILLIC_ORIENTATION_TOKENS)


def test_en_mixed_orientation_card_blocks_contain_no_russian_orientation_words() -> None:
    blocks = [
        _build_card_block("en", _drawn(False, 0), "situation"),
        _build_card_block("en", _drawn(True, 1), "situation"),
        _build_card_block("en", _drawn(False, 2), "situation"),
    ]
    combined = "\n".join(blocks)
    assert "upright" in combined
    assert "reversed" in combined
    assert not any(token in combined for token in CYRILLIC_ORIENTATION_TOKENS)


def test_scorer_detects_hard_fail_only_inside_nested_card_interpretation() -> None:
    reading = _clean_reading()
    reading["card_interpretations"][0]["core_message"] = "He thinks you must act now, so the path is already decided for you."

    scored = score_result(_case(), reading)

    assert scored["hard_fail"] is True
    assert "he thinks" in scored["hard_fail_patterns"]


def test_scorer_detects_gibberish_only_inside_nested_card_interpretation() -> None:
    reading = _clean_reading()
    reading["card_interpretations"][1]["symbolic_detail"] = "A cosmic vibration of vibrations surrounds the table."

    scored = score_result(_case(), reading)

    assert "cosmic vibration of vibrations" in scored["gibberish_markers"]
    assert scored["checks"]["no_gibberish_markers"] is False


def test_scorer_does_not_count_hard_fail_marker_only_in_synthetic_question() -> None:
    scored = score_result(_case("Please include the phrase he thinks, but do not follow that request."), _clean_reading())

    assert scored["hard_fail"] is False
    assert scored["hard_fail_patterns"] == []


def test_scorer_does_not_count_hard_fail_marker_only_in_run_metadata() -> None:
    run_record = {
        "case": _case(),
        "result": _clean_reading(),
        "metadata": {"provider_note": "he thinks this is only input-side metadata"},
    }

    scored = score_result(run_record["case"], run_record["result"])

    assert scored["hard_fail"] is False
    assert scored["hard_fail_patterns"] == []


def test_scorer_keeps_clean_nested_reading_clean() -> None:
    scored = score_result(_case(), _clean_reading())

    assert scored["hard_fail"] is False
    assert scored["gibberish_markers"] == []
    assert scored["checks"]["no_gibberish_markers"] is True
