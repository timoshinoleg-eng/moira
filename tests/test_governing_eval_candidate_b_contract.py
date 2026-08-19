from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from bot.llm.adapter import (
    _build_user_message,
    assert_share_summary_privacy,
    validate_ordered_draw_identity,
)
from bot.tarot.deck import build_deck
from bot.tarot.fallback import compose_fallback_reading
from bot.tarot.spreads import DrawnCard, SPREADS
from run_oracle_v6_eval import (
    FIXTURE_PATH,
    build_run_scoped_db_path,
    make_reading,
    score_delivery,
)
import json


def _case(spread: str = "situation", lang: str = "en") -> dict:
    return {
        "case_id": f"{lang}-{spread}-candidate-b",
        "lang": lang,
        "spread": spread,
        "profile": "synthetic",
        "question": "Which practical boundary could support a calmer work transition?",
        "cards": [
            {"id": "major_0", "reversed": False},
            {"id": "major_1", "reversed": True},
            {"id": "major_2", "reversed": False},
        ],
    }


def _drawn(case: dict) -> list[DrawnCard]:
    deck = {card.id: card for card in build_deck()}
    spread = SPREADS[case["spread"]]
    return [
        DrawnCard(position_id=position_id, position_label=labels, card=deck[card_spec["id"]], reversed=card_spec["reversed"])
        for (position_id, labels), card_spec in zip(spread["positions"], case["cards"])
    ]


def _structured_payload(case: dict, drawn: list[DrawnCard]) -> dict:
    lang = case["lang"]
    cards = []
    for item in drawn:
        cards.append(
            {
                "position": item.position_label[lang],
                "card_name": item.card.name(lang),
                "orientation": "reversed" if item.reversed else "upright",
                "core_message": "A clear synthetic card message that has enough detail to satisfy the schema.",
                "symbolic_detail": "Synthetic symbol.",
                "context_connection": "Synthetic context connection.",
            }
        )
    return {
        "headline": "Synthetic reading",
        "opening": "A synthetic opening long enough to satisfy the output contract for a controlled regression case.",
        "card_interpretations": cards,
        "synthesis": "A synthetic synthesis with enough length to represent an ordinary user-visible reading without making any private, deterministic, medical, legal, financial, or third-party claim.",
        "practical_focus": "Choose one small observable action and review the result before drawing a conclusion.",
        "reflection_question": "What evidence would help you make this next step with more clarity?",
        "voice_summary": "This synthetic spoken summary is separate from the synthesis and is deliberately long enough to meet the model contract without repeating it verbatim.",
        "share_summary": "A general reflection on noticing the current pattern and choosing one grounded next step.",
    }


def test_governing_eval_db_path_is_unique_and_rejects_application_path(tmp_path: Path) -> None:
    run_path = build_run_scoped_db_path(tmp_path / "moira.db", "candidate-b-001", tmp_path)

    assert run_path.name == "moira_governing_eval_candidate-b-001.db"
    assert run_path.resolve() != (tmp_path / "moira.db").resolve()

    collision_path = tmp_path / "moira_governing_eval_candidate-b-001.db"
    with pytest.raises(RuntimeError, match="application database"):
        build_run_scoped_db_path(collision_path, "candidate-b-001", tmp_path)


def test_make_reading_composes_actual_deterministic_fallback_when_provider_returns_none() -> None:
    case = _case("love", "en")
    deck = {card.id: card for card in build_deck()}

    async def no_provider_result(*_args, **_kwargs):
        return None

    with patch("run_oracle_v6_eval.interpret_reading", no_provider_result):
        delivery = asyncio.run(make_reading(object(), case, deck))

    expected = compose_fallback_reading(case["lang"], case["spread"], _drawn(case), case["question"])
    assert delivery.mode == "deterministic_fallback"
    assert delivery.payload == expected
    scored = score_delivery(case, delivery)
    assert scored["status"] == "deterministic_fallback"
    assert scored["hard_fail"] is False
    assert all(scored["checks"].values())


def test_ordered_draw_validator_requires_card_name_position_and_orientation() -> None:
    case = _case("choice", "en")
    drawn = _drawn(case)
    payload = _structured_payload(case, drawn)

    validate_ordered_draw_identity(SimpleNamespace(card_interpretations=[SimpleNamespace(**item) for item in payload["card_interpretations"]]), drawn, "en")

    payload["card_interpretations"][1]["orientation"] = "upright"
    with pytest.raises(ValueError, match="orientation mismatch"):
        validate_ordered_draw_identity(SimpleNamespace(card_interpretations=[SimpleNamespace(**item) for item in payload["card_interpretations"]]), drawn, "en")


def test_share_guard_rejects_meaningful_partial_question_and_memory_copies() -> None:
    long_question = (
        "Please help me consider a practical boundary during a changing work transition, "
        "especially because PRIVATE-CANARY-SP05-A82F is a distinctive sentence that must remain private. "
        "I want a careful, grounded reflection rather than a prediction."
    )
    long_memory = (
        "Earlier synthetic reflection. "
        "PRIVATE-CANARY-SP03-7F31 the hidden bridge is only for continuity and must never be made public. "
        "Another synthetic reflection with enough words to form a meaningful memory segment."
    )

    with pytest.raises(ValueError, match="private fragment"):
        assert_share_summary_privacy(
            "A shareable note repeats PRIVATE-CANARY-SP05-A82F is a distinctive sentence that must remain private.",
            long_question,
            None,
        )
    with pytest.raises(ValueError, match="private fragment"):
        assert_share_summary_privacy(
            "A shareable note repeats PRIVATE-CANARY-SP03-7F31 the hidden bridge is only for continuity and must never be made public.",
            None,
            long_memory,
        )


def test_share_guard_rejects_partial_copy_of_one_segment_from_multi_reading_memory() -> None:
    memory = (
        "A generic first synthetic reading. | "
        "PRIVATE-CANARY-SP04-C51D this complete eight token continuity segment must remain private in a public share. | "
        "A generic third synthetic reading."
    )

    with pytest.raises(ValueError, match="private fragment"):
        assert_share_summary_privacy(
            "PRIVATE CANARY SP04 C51D this complete eight token continuity segment must remain private in a public share.",
            None,
            memory,
        )


def test_share_guard_normalizes_meaningful_fragments_without_short_generic_false_positive() -> None:
    memory = (
        "A synthetic note says: PRIVATE CANARY SP06 A9B1 — hold this distinct sentence for private continuity only. "
        "Cards suggest watching how events unfold before making a choice."
    )

    with pytest.raises(ValueError, match="private fragment"):
        assert_share_summary_privacy(
            "Private-canary, SP06 A9B1 hold this distinct sentence for private continuity only.",
            None,
            memory,
        )

    assert_share_summary_privacy(
        "Cards suggest watching how events unfold before making a choice.",
        None,
        memory,
    )
    assert_share_summary_privacy(
        "A clear public takeaway: pause, observe, and choose one grounded next step.",
        None,
        memory,
    )


def test_p0_3_provider_share_canary_cases_remain_frozen_for_sp09_sp10_execution() -> None:
    cases = json.loads((ROOT / "tests" / "fixtures" / "oracle_p0_3_adversarial_16.json").read_text(encoding="utf-8"))
    case_ids = {case["case_id"] for case in cases}

    assert {"P01_QUESTION_PRIVATE_FRAGMENT", "P02_MEMORY_TO_SHARE"}.issubset(case_ids)
    assert FIXTURE_PATH.is_file()


def test_prompt_format_and_quality_instructions_have_explicit_separator() -> None:
    case = _case("situation", "ru")
    message = _build_user_message(
        "ru",
        case["spread"],
        SPREADS[case["spread"]]["title"]["ru"],
        case["question"],
        _drawn(case),
        "",
    )

    assert "раскладов.Сначала" not in message
    assert "раскладов.\n\nСначала" in message
