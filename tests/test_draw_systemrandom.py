"""QW-1: ordinary draws use secrets.SystemRandom; daily_card stays deterministic."""
from __future__ import annotations

import os
import random
import secrets
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_draw_is_reproducible_with_fixed_rng(monkeypatch) -> None:
    from bot.tarot import spreads

    assert isinstance(spreads._rng, secrets.SystemRandom)
    monkeypatch.setattr(spreads, "_rng", random.Random(1234))
    first = [(d.card.id, d.reversed) for d in spreads.draw("love")]
    monkeypatch.setattr(spreads, "_rng", random.Random(1234))
    second = [(d.card.id, d.reversed) for d in spreads.draw("love")]
    assert first == second


def test_deck_invariant_78_unique_cards() -> None:
    from bot.tarot.deck import build_deck
    from bot.tarot.spreads import draw

    deck = build_deck()
    assert len(deck) == 78
    assert len({c.id for c in deck}) == 78
    drawn = draw("situation")
    assert len(drawn) == 3
    assert len({d.card.id for d in drawn}) == 3


def test_daily_card_stays_deterministic() -> None:
    from bot.astro.calc import daily_card

    day = date(2026, 1, 4)
    first = daily_card(day, 42)
    second = daily_card(day, 42)
    assert (first[0].id, first[1]) == (second[0].id, second[1])
    # Independent oracle: seeded random.Random, untouched by the shuffle change.
    rng = random.Random(day.isoformat() + "#" + str(42))
    from bot.tarot.deck import build_deck

    deck = build_deck()
    expected = deck[rng.randrange(len(deck))]
    assert first[0].id == expected.id
    assert first[1] == (rng.random() < 0.33)
