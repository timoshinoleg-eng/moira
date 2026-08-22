from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from bot.llm.adapter import SPREAD_RULES_EN, SPREAD_RULES_RU, _build_user_message
from bot.tarot.deck import build_deck
from bot.tarot.spreads import DrawnCard, SPREADS
from run_oracle_v6_eval import make_reading


class _Result:
    def model_dump(self) -> dict:
        return {"status": "synthetic"}


def _case(spread: str, lang: str) -> dict:
    return {
        "case_id": f"{lang}-{spread}-contract",
        "lang": lang,
        "spread": spread,
        "question": "Synthetic prompt-contract question.",
        "cards": [
            {"id": "major_0", "reversed": False},
            {"id": "major_1", "reversed": False},
            {"id": "major_2", "reversed": True},
        ],
    }


def test_eval_harness_passes_fixture_spread_id_to_interpretation() -> None:
    case = _case("choice", "en")
    deck = {card.id: card for card in build_deck()}
    observed: dict[str, object] = {}

    async def fake_interpret(*args, **kwargs):
        observed["spread_id"] = kwargs.get("spread_id")
        return _Result()

    with patch("run_oracle_v6_eval.interpret_reading", fake_interpret):
        result = asyncio.run(make_reading(object(), case, deck))

    assert result.mode == "llm_structured"
    assert result.payload == {"status": "synthetic"}
    assert observed["spread_id"] == "choice"


def test_all_spread_rules_are_included_when_eval_uses_fixture_spread_id() -> None:
    deck = {card.id: card for card in build_deck()}

    for lang, rules in (("ru", SPREAD_RULES_RU), ("en", SPREAD_RULES_EN)):
        for spread_id, expected_rule in rules.items():
            spread = SPREADS[spread_id]
            drawn = [
                DrawnCard(
                    position_id=position_id,
                    position_label=labels,
                    card=deck[card_id],
                    reversed=False,
                )
                for (position_id, labels), card_id in zip(
                    spread["positions"], ("major_0", "major_1", "major_2")
                )
            ]
            message = _build_user_message(
                lang,
                spread_id,
                spread["title"][lang],
                "Synthetic question.",
                drawn,
                "",
            )
            assert expected_rule in message
