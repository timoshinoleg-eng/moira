from __future__ import annotations

import random
from dataclasses import dataclass

from .deck import TarotCard, build_deck

SPREADS = {
    "situation": {
        "title": {"ru": "Расклад «Ситуация»", "en": "“Situation” spread"},
        "desc": {
            "ru": "Три карты: суть происходящего, скрытый фактор и следующий шаг.",
            "en": "Three cards: what is really going on, a hidden factor, and the next step.",
        },
        "positions": [
            ("essence", {"ru": "Суть ситуации", "en": "The essence"}),
            ("hidden", {"ru": "Скрытый фактор", "en": "Hidden factor"}),
            ("next_step", {"ru": "Следующий шаг", "en": "Next step"}),
        ],
    },
    "love": {
        "title": {"ru": "Расклад «Любовь»", "en": "“Love” spread"},
        "desc": {
            "ru": "Три карты: твоё состояние, динамика связи и полезный фокус.",
            "en": "Three cards: your state, the relationship dynamic, and a helpful focus.",
        },
        "positions": [
            ("you", {"ru": "Твоё состояние", "en": "Your state"}),
            ("dynamic", {"ru": "Динамика связи", "en": "Relationship dynamic"}),
            ("focus", {"ru": "Полезный фокус", "en": "Helpful focus"}),
        ],
    },
    "choice": {
        "title": {"ru": "Расклад «Выбор»", "en": "“Choice” spread"},
        "desc": {
            "ru": "Три карты: потенциал пути А, потенциал пути Б и критерий решения.",
            "en": "Three cards: potential of path A, potential of path B, and a decision criterion.",
        },
        "positions": [
            ("path_a", {"ru": "Путь А", "en": "Path A"}),
            ("path_b", {"ru": "Путь Б", "en": "Path B"}),
            ("criterion", {"ru": "Критерий решения", "en": "Decision criterion"}),
        ],
    },
}

# Human-readable position explanations for LLM prompt
POSITION_MEANINGS = {
    "situation": {
        "essence": {
            "ru": "суть того, что происходит сейчас, внешний или внутренний процесс",
            "en": "the essence of what is happening now, an outer or inner process",
        },
        "hidden": {
            "ru": "скрытый фактор, внутреннее препятствие или то, что пользователь пока не замечает",
            "en": "a hidden factor, an inner obstacle, or something the user has not yet noticed",
        },
        "next_step": {
            "ru": "наиболее конструктивный следующий шаг или направление внимания",
            "en": "the most constructive next step or direction of attention",
        },
    },
    "love": {
        "you": {
            "ru": "состояние, потребности и вклад пользователя в отношения",
            "en": "the user's state, needs, and contribution to the relationship",
        },
        "dynamic": {
            "ru": "динамика связи, воспринимаемая сторона отношений или то, что связывает двоих",
            "en": "the relationship dynamic, the perceived side, or what connects the two",
        },
        "focus": {
            "ru": "полезный фокус — что стоит поддерживать или ослабить",
            "en": "a helpful focus — what to nurture or ease up on",
        },
    },
    "choice": {
        "path_a": {
            "ru": "потенциал, возможности и цена первого пути",
            "en": "the potential, opportunities, and cost of the first path",
        },
        "path_b": {
            "ru": "потенциал, возможности и цена второго пути",
            "en": "the potential, opportunities, and cost of the second path",
        },
        "criterion": {
            "ru": "критерий решения или то, что пользователь может недооценивать",
            "en": "a decision criterion or something the user may be underestimating",
        },
    },
}

REVERSED_CHANCE = 0.33

SPREAD_VERSION = "v1"
DRAW_ENGINE_VERSION = "v1"


@dataclass
class DrawnCard:
    position_id: str
    position_label: dict  # {"ru": ..., "en": ...}
    card: TarotCard
    reversed: bool


def draw(spread_id: str) -> list[DrawnCard]:
    if spread_id not in SPREADS:
        raise ValueError(f"Unknown spread: {spread_id}")
    deck = build_deck()
    random.shuffle(deck)
    picked = deck[: len(SPREADS[spread_id]["positions"])]
    result = []
    for (pos_id, labels), card in zip(SPREADS[spread_id]["positions"], picked):
        result.append(
            DrawnCard(
                position_id=pos_id,
                position_label=labels,
                card=card,
                reversed=random.random() < REVERSED_CHANCE,
            )
        )
    return result


def position_meaning(spread_id: str, position_id: str, lang: str) -> str:
    """Return a human-readable explanation of a position's meaning for the LLM prompt."""
    lang = lang if lang in ("ru", "en") else "ru"
    spread = POSITION_MEANINGS.get(spread_id, {})
    pos = spread.get(position_id, {})
    return pos.get(lang, position_id)
