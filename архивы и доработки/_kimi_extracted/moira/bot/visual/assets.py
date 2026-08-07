from __future__ import annotations

import pathlib

from ..tarot.deck import TarotCard

ASSETS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "cards"

SUIT_LETTER = {"cups": "c", "wands": "w", "swords": "s", "pentacles": "p"}
RANK_NUM = {
    "ace": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "page": 11, "knight": 12, "queen": 13, "king": 14,
}


def card_image_path(card: TarotCard) -> pathlib.Path | None:
    if card.arcana == "major":
        num = int(card.id.split("_", 1)[1])
        p = ASSETS_DIR / f"m{num:02d}.jpg"
    else:
        letter = SUIT_LETTER.get(card.suit or "")
        rank_num = RANK_NUM.get(card.rank or "")
        if not letter or not rank_num:
            return None
        p = ASSETS_DIR / f"{letter}{rank_num:02d}.jpg"
    return p if p.exists() else None


def check_assets() -> tuple[int, int]:
    """Return (found, expected=78)."""
    found = 0
    from ..tarot.deck import build_deck

    for card in build_deck():
        if card_image_path(card) is not None:
            found += 1
    return found, 78
