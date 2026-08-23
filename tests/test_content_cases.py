"""Content-case tests: 48 deterministic fallback readings (no LLM).

Each scenario in tests/content_cases.json is composed via
compose_fallback_reading() and checked against the expect-flags:
positions referenced, reversal distinguished, synthesis present, no claims
about another person's thoughts, reflection question present, length limit.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from bot.tarot.deck import deck_index
from bot.tarot.fallback import compose_fallback_reading
from bot.tarot.spreads import SPREADS, DrawnCard

CASES = json.loads(
    (pathlib.Path(__file__).parent / "content_cases.json").read_text(encoding="utf-8")
)
INDEX = deck_index()

FORBIDDEN_RU = [
    "он думает", "она думает", "он считает", "она считает",
    "он чувствует", "она чувствует", "он уверен", "она уверена",
    "он знает", "она знает", "он хочет", "она хочет",
]
FORBIDDEN_EN = [
    "he thinks", "she thinks", "he believes", "she believes",
    "he feels", "she feels", "he is sure", "she is sure",
    "he knows", "she knows", "he wants", "she wants",
]


def _build_drawn(spread_id: str, lang: str, cards: list[dict]) -> list[DrawnCard]:
    positions = SPREADS[spread_id]["positions"]
    drawn = []
    for i, card in enumerate(cards):
        pos_id, labels = positions[i]
        drawn.append(
            DrawnCard(
                position_id=pos_id,
                position_label=labels,
                card=INDEX[card["id"]],
                reversed=bool(card["reversed"]),
            )
        )
    return drawn


def _full_text(result: dict) -> str:
    return " ".join(
        [result["headline"], result["opening"], " ".join(result["card_texts"]),
         result["synthesis"], result["practical_focus"], result["reflection_question"]]
    )


def test_all_cases_have_expected_structure() -> None:
    assert len(CASES) == 48, f"expected 48 scenarios, got {len(CASES)}"
    for c in CASES:
        assert set(c) >= {"id", "spread", "lang", "question", "cards", "expect"}
        assert c["spread"] in SPREADS, c["id"]
        assert c["lang"] in ("ru", "en"), c["id"]
        assert len(c["cards"]) == 3, c["id"]
        for card in c["cards"]:
            assert card["id"] in INDEX, f"{c['id']}: unknown card {card['id']}"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_content_case(case: dict) -> None:
    drawn = _build_drawn(case["spread"], case["lang"], case["cards"])
    result = compose_fallback_reading(case["lang"], case["spread"], drawn, case["question"])
    exp = case["expect"]
    text = _full_text(result)
    low = text.lower()

    if exp.get("must_reference_positions", True):
        positions = SPREADS[case["spread"]]["positions"]
        labels = [pos[1].get(case["lang"], pos[1]["ru"]) for pos in positions]
        for label in labels:
            assert label in text, f"{case['id']}: position label '{label}' missing"

    if exp.get("must_distinguish_reversal", True):
        # 1) each card's text uses the orientation-specific meaning
        for d in drawn:
            entry = next(
                ct for ct in result["card_texts"]
                if d.position_label.get(case["lang"], d.position_label["ru"]) in ct
            )
            assert d.card.meaning(case["lang"], d.reversed) in entry, (
                f"{case['id']}: orientation-specific meaning not used for {d.card.id}"
            )
        # 2) flipping all orientations changes the card texts
        flipped = [
            DrawnCard(position_id=d.position_id, position_label=d.position_label,
                      card=d.card, reversed=not d.reversed)
            for d in drawn
        ]
        flipped_result = compose_fallback_reading(case["lang"], case["spread"], flipped, case["question"])
        assert flipped_result["card_texts"] != result["card_texts"], (
            f"{case['id']}: reversal does not change the reading"
        )

    if exp.get("must_include_synthesis", True):
        assert len(result["synthesis"]) >= 100, f"{case['id']}: synthesis too short"

    if exp.get("must_not_assert_other_person_thoughts", True):
        forbidden = FORBIDDEN_RU if case["lang"] == "ru" else FORBIDDEN_EN
        hits = [f for f in forbidden if f in low]
        assert not hits, f"{case['id']}: asserts other-person state: {hits}"

    if exp.get("must_include_reflection_question", True):
        assert result["reflection_question"].strip().endswith("?"), (
            f"{case['id']}: reflection question missing"
        )

    if exp.get("maximum_length"):
        assert len(text) <= exp["maximum_length"], (
            f"{case['id']}: {len(text)} chars > {exp['maximum_length']}"
        )
