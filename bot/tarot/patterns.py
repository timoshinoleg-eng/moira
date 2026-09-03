"""Deterministic card-pattern analyzer. Zero LLM calls.

Produces a short (max 6 lines) supporting-context block for the reading prompt:
arcana balance, suit distribution with a dominant suit only on a clear lead,
reversed count, and keywords literally shared between drawn cards.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SUIT_NAMES = {
    "wands": {"ru": "Жезлы", "en": "Wands"},
    "cups": {"ru": "Кубки", "en": "Cups"},
    "swords": {"ru": "Мечи", "en": "Swords"},
    "pentacles": {"ru": "Пентакли", "en": "Pentacles"},
}

_MAX_SHARED_LINES = 2


@dataclass(frozen=True)
class PatternSummary:
    major_count: int = 0
    minor_count: int = 0
    suit_counts: dict[str, int] = field(default_factory=dict)
    dominant_suit: str | None = None
    reversed_count: int = 0
    shared_keywords: tuple[tuple[str, str, tuple[str, ...]], ...] = ()
    positions: tuple[str, ...] = ()


def analyze_patterns(drawn, lang: str = "ru") -> PatternSummary:
    """Compute pattern facts from drawn cards. Same input always gives same output."""
    lang = lang if lang in ("ru", "en") else "ru"
    major_count = 0
    suit_counts: dict[str, int] = {}
    reversed_count = 0
    positions: list[str] = []
    keyword_sets: list[tuple[str, set[str]]] = []
    for card in drawn:
        if card.card.arcana == "major":
            major_count += 1
        elif card.card.suit:
            suit_counts[card.card.suit] = suit_counts.get(card.card.suit, 0) + 1
        if card.reversed:
            reversed_count += 1
        positions.append(card.position_id)
        words = {w.casefold() for w in card.card.keywords(lang) if w}
        keyword_sets.append((card.card.name(lang), words))
    minor_count = len(drawn) - major_count
    dominant_suit: str | None = None
    if suit_counts:
        top = max(suit_counts.values())
        leaders = [suit for suit, count in suit_counts.items() if count == top]
        if len(leaders) == 1 and top >= 2:
            dominant_suit = leaders[0]
    shared: list[tuple[str, str, tuple[str, ...]]] = []
    for i in range(len(keyword_sets)):
        for j in range(i + 1, len(keyword_sets)):
            common = sorted(keyword_sets[i][1] & keyword_sets[j][1])
            if common:
                shared.append((keyword_sets[i][0], keyword_sets[j][0], tuple(common)))
    return PatternSummary(
        major_count=major_count,
        minor_count=minor_count,
        suit_counts=dict(sorted(suit_counts.items())),
        dominant_suit=dominant_suit,
        reversed_count=reversed_count,
        shared_keywords=tuple(shared),
        positions=tuple(positions),
    )


def format_pattern_block(summary: PatternSummary, lang: str = "ru") -> str:
    """Render the prompt block: 6 lines max, supporting context only."""
    lang = lang if lang in ("ru", "en") else "ru"
    total = summary.major_count + summary.minor_count
    if total == 0:
        return ""
    if lang == "ru":
        lines = ["Связи между картами: используй только как поддерживающий контекст, "
                 "не выдумывай дополнительные паттерны."]
        lines.append(f"Старших Арканов: {summary.major_count} из {total}; младших: {summary.minor_count} из {total}.")
        if summary.suit_counts:
            suits = ", ".join(f"{SUIT_NAMES[s]['ru']} {c}" for s, c in summary.suit_counts.items())
            dominant = f" Преобладает: {SUIT_NAMES[summary.dominant_suit]['ru']}." if summary.dominant_suit else ""
            lines.append(f"Масти: {suits}.{dominant}")
        lines.append(f"Перевёрнутых карт: {summary.reversed_count} из {total}.")
        for name_a, name_b, words in summary.shared_keywords[:_MAX_SHARED_LINES]:
            lines.append(f"Общая тема «{', '.join(words)}»: {name_a} и {name_b}.")
    else:
        lines = ["Links between the cards: use only as supporting context, "
                 "do not invent additional patterns."]
        lines.append(f"Major Arcana: {summary.major_count} of {total}; minor: {summary.minor_count} of {total}.")
        if summary.suit_counts:
            suits = ", ".join(f"{SUIT_NAMES[s]['en']} {c}" for s, c in summary.suit_counts.items())
            dominant = f" Dominant: {SUIT_NAMES[summary.dominant_suit]['en']}." if summary.dominant_suit else ""
            lines.append(f"Suits: {suits}.{dominant}")
        lines.append(f"Reversed cards: {summary.reversed_count} of {total}.")
        for name_a, name_b, words in summary.shared_keywords[:_MAX_SHARED_LINES]:
            lines.append(f"Shared theme “{', '.join(words)}”: {name_a} and {name_b}.")
    return "\n".join(lines[:6])
