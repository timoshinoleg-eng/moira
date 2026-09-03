"""Validate the S1/S2 minor-arcana content drop against TASKS_SOL.md requirements.

Usage: uv run python scripts/validate_minor_content.py
Exit 0 = valid (or nothing delivered yet), exit 1 = violations found.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.tarot.data_minor import MINOR_KEYWORDS, SUITS  # noqa: E402
from bot.tarot.data_symbols import MINOR_SYMBOLS  # noqa: E402

SUITS_IDS = ("wands", "cups", "swords", "pentacles")
RANKS = ("ace", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "page", "knight", "queen", "king")
EXPECTED_IDS = [f"{s}_{r}" for s in SUITS_IDS for r in RANKS]

SUIT_THEME_RU = {
    "wands": {"действие", "вдохновение", "энергия"},
    "cups": {"эмоции", "отношения", "интуиция"},
    "swords": {"мысли", "решения", "конфликт"},
    "pentacles": {"деньги", "работа", "ресурсы"},
}
SUIT_THEME_EN = {
    "wands": {"action", "inspiration", "drive"},
    "cups": {"emotions", "relationships", "intuition"},
    "swords": {"thoughts", "decisions", "conflict"},
    "pentacles": {"money", "work", "resources"},
}
ABSTRACT_RU = {"сила", "судьба", "энергия", "путь", "выбор"}
ABSTRACT_EN = {"strength", "fate", "destiny", "energy", "path", "choice"}
SUIT_NAME_STEMS = {"жезл", "куб", "меч", "мечи", "пентакл", "wand", "cup", "sword", "pentacle"}
RANK_STEMS = {"туз", "двой", "трой", "четвёр", "пятёр", "шестёр", "семёр", "восьмёр",
              "девят", "десят", "паж", "рыцар", "королев", "корол",
              "ace", "two", "three", "four", "five", "six", "seven", "eight",
              "nine", "ten", "page", "knight", "queen", "king"}

LATIN_RE = re.compile(r"[A-Za-z]")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
TEXT_RE = re.compile(r"^[\w\s'’\-.,]+$", re.UNICODE)


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-zА-Яа-яЁё]+", text.casefold())


def _check_list(card_id: str, lang: str, items: object, *, min_words: int, max_words: int,
                errors: list[str]) -> list[str]:
    prefix = f"{card_id}.{lang}"
    if not isinstance(items, list) or len(items) != 3:
        errors.append(f"{prefix}: expected exactly 3 elements, got {items!r}")
        return []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{prefix}: empty element")
            continue
        if item != item.strip():
            errors.append(f"{prefix}: leading/trailing whitespace in {item!r}")
        if "—" in item:
            errors.append(f"{prefix}: em dash forbidden in {item!r}")
        if not TEXT_RE.match(item):
            errors.append(f"{prefix}: non-text characters (emoji?) in {item!r}")
        if any(ch.isalpha() and ch != ch.lower() for ch in item):
            errors.append(f"{prefix}: must be lowercase: {item!r}")
        if lang == "ru" and LATIN_RE.search(item):
            errors.append(f"{prefix}: latin letters in RU string: {item!r}")
        if lang == "en" and CYRILLIC_RE.search(item):
            errors.append(f"{prefix}: cyrillic letters in EN string: {item!r}")
        n_words = len(item.split())
        if not min_words <= n_words <= max_words:
            errors.append(f"{prefix}: expected {min_words}-{max_words} words, got {n_words} in {item!r}")
    return [i for i in items if isinstance(i, str)]


def validate() -> list[str]:
    errors: list[str] = []
    for name, payload in (("MINOR_SYMBOLS", MINOR_SYMBOLS), ("MINOR_KEYWORDS", MINOR_KEYWORDS)):
        if set(payload) != set(EXPECTED_IDS):
            errors.append(f"{name}: expected 56 card ids, missing={sorted(set(EXPECTED_IDS) - set(payload))[:5]}, "
                          f"extra={sorted(set(payload) - set(EXPECTED_IDS))[:5]}")
    # S1 symbols.
    seen_per_suit: dict[str, dict[str, str]] = {s: {} for s in SUITS_IDS}
    for card_id in EXPECTED_IDS:
        entry = MINOR_SYMBOLS.get(card_id)
        if not isinstance(entry, dict):
            errors.append(f"MINOR_SYMBOLS[{card_id}]: missing entry")
            continue
        suit = card_id.split("_")[0]
        for lang in ("ru", "en"):
            items = _check_list(card_id, lang, entry.get(lang), min_words=1, max_words=4, errors=errors)
            abstract = ABSTRACT_RU if lang == "ru" else ABSTRACT_EN
            for item in items:
                words = set(_words(item))
                if words & abstract:
                    errors.append(f"MINOR_SYMBOLS {card_id}.{lang}: abstraction in {item!r}")
                if words & SUIT_NAME_STEMS:
                    errors.append(f"MINOR_SYMBOLS {card_id}.{lang}: suit name in {item!r}")
                if words & RANK_STEMS:
                    errors.append(f"MINOR_SYMBOLS {card_id}.{lang}: rank name in {item!r}")
                key = item.casefold()
                if key in seen_per_suit[suit]:
                    errors.append(f"MINOR_SYMBOLS {card_id}.{lang}: {item!r} repeats "
                                  f"{seen_per_suit[suit][key]} within suit {suit}")
                else:
                    seen_per_suit[suit][key] = card_id
    # S2 keywords.
    kw_sets: dict[str, dict[str, set[str]]] = {s: {} for s in SUITS_IDS}
    for card_id in EXPECTED_IDS:
        entry = MINOR_KEYWORDS.get(card_id)
        if not isinstance(entry, dict):
            errors.append(f"MINOR_KEYWORDS[{card_id}]: missing entry")
            continue
        suit = card_id.split("_")[0]
        for lang, theme in (("ru", SUIT_THEME_RU[suit]), ("en", SUIT_THEME_EN[suit])):
            items = _check_list(f"kw:{card_id}", lang, entry.get(f"kw_{lang}"),
                                min_words=1, max_words=2, errors=errors)
            for item in items:
                if set(_words(item)) & theme:
                    errors.append(f"MINOR_KEYWORDS {card_id}.{lang}: suit-theme word in {item!r}")
            kw_sets[suit].setdefault(lang, {}).__setitem__(
                card_id, {w for item in items for w in _words(item)})
    for suit in SUITS_IDS:
        for lang in ("ru", "en"):
            ids = sorted(kw_sets[suit].get(lang, {}))
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    shared = kw_sets[suit][lang][ids[i]] & kw_sets[suit][lang][ids[j]]
                    if len(shared) >= 2:
                        errors.append(f"MINOR_KEYWORDS {suit}.{lang}: {ids[i]} and {ids[j]} "
                                      f"share {sorted(shared)}")
    assert set(SUITS) == set(SUITS_IDS)  # content model used the same suit table
    return errors


def main() -> int:
    if not MINOR_SYMBOLS and not MINOR_KEYWORDS:
        print("no S1/S2 content delivered yet — nothing to validate")
        return 0
    errors = validate()
    if errors:
        print(f"{len(errors)} violations:")
        for err in errors[:50]:
            print(f"  - {err}")
        return 1
    print("S1/S2 content valid: 56 symbols + 56 keyword sets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
