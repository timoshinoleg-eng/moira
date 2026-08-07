from __future__ import annotations

from dataclasses import dataclass, field

from .data_major import MAJOR
from .data_minor import (
    COURT_SUIT_VARIANTS,
    RANK_SUIT_VARIANTS,
    SUITS,
    COURT_NAMES_EN,
    COURT_NAMES_RU,
    RANK_NAMES_EN,
    RANK_NAMES_RU,
)
from .data_symbols import MAJOR_SYMBOLS, MAJOR_REFLECTION


@dataclass
class CardMeanings:
    """Upright and reversed meanings of a card in one language."""

    essence: str = ""
    keywords: list[str] = field(default_factory=list)
    light: str = ""
    shadow: str = ""
    advice: str = ""
    blocked_expression: str = ""
    excess_or_deficit: str = ""
    relationship: str = ""
    career: str = ""
    inner_state: str = ""
    decision: str = ""


@dataclass
class LocalizedCard:
    """Fully localized card content for a single language."""

    upright: CardMeanings = field(default_factory=CardMeanings)
    reversed: CardMeanings = field(default_factory=CardMeanings)
    symbols: list[str] = field(default_factory=list)
    reflection_question: str = ""


@dataclass
class TarotCard:
    id: str
    name_ru: str
    name_en: str
    arcana: str  # major | minor
    suit: str | None = None
    rank: str | None = None
    keywords_ru: list[str] = field(default_factory=list)
    keywords_en: list[str] = field(default_factory=list)
    meanings: dict = field(default_factory=dict)
    ru: LocalizedCard = field(default_factory=LocalizedCard)
    en: LocalizedCard = field(default_factory=LocalizedCard)

    def name(self, lang: str) -> str:
        return self.name_ru if lang == "ru" else self.name_en

    def keywords(self, lang: str) -> list[str]:
        return self.keywords_ru if lang == "ru" else self.keywords_en

    def meaning(self, lang: str, reversed_: bool) -> str:
        lang = lang if lang in self.meanings else "ru"
        return self.meanings[lang]["reversed" if reversed_ else "upright"]

    def localized(self, lang: str) -> LocalizedCard:
        return self.ru if lang == "ru" else self.en


_DECK_INDEX: dict[str, TarotCard] | None = None


def deck_index() -> dict[str, TarotCard]:
    global _DECK_INDEX
    if _DECK_INDEX is None:
        _DECK_INDEX = {c.id: c for c in build_deck()}
    return _DECK_INDEX


def cards_from_codes(codes: list[str]) -> list[tuple[TarotCard, bool]]:
    """Parse stored codes like 'major_0' / 'major_0R' into (card, reversed) pairs."""
    index = deck_index()
    out: list[tuple[TarotCard, bool]] = []
    for code in codes:
        reversed_ = code.endswith("R")
        card = index.get(code[:-1] if reversed_ else code)
        if card is not None:
            out.append((card, reversed_))
    return out


def _build_major(m: dict) -> TarotCard:
    num = m["num"]
    symbols = MAJOR_SYMBOLS.get(num, {})
    reflection = MAJOR_REFLECTION.get(num, {})
    return TarotCard(
        id=f"major_{num}",
        name_ru=m["name_ru"],
        name_en=m["name_en"],
        arcana="major",
        suit=None,
        rank=None,
        keywords_ru=m["kw_ru"],
        keywords_en=m["kw_en"],
        meanings={
            "ru": {"upright": m["ru_upr"], "reversed": m["ru_rev"]},
            "en": {"upright": m["en_upr"], "reversed": m["en_rev"]},
        },
        ru=LocalizedCard(
            upright=CardMeanings(essence=m["ru_upr"], keywords=m["kw_ru"]),
            reversed=CardMeanings(essence=m["ru_rev"], keywords=m["kw_ru"]),
            symbols=symbols.get("ru", []),
            reflection_question=reflection.get("ru", ""),
        ),
        en=LocalizedCard(
            upright=CardMeanings(essence=m["en_upr"], keywords=m["kw_en"]),
            reversed=CardMeanings(essence=m["en_rev"], keywords=m["kw_en"]),
            symbols=symbols.get("en", []),
            reflection_question=reflection.get("en", ""),
        ),
    )


def _build_minor(suit_id: str, suit: dict, rank_id: str, rank_name_ru: str, rank_name_en: str,
                 ru_upr: str, ru_rev: str, en_upr: str, en_rev: str) -> TarotCard:
    return TarotCard(
        id=f"{suit_id}_{rank_id}",
        name_ru=f"{rank_name_ru} {suit['ru_gen']}",
        name_en=f"{rank_name_en} of {suit['en']}",
        arcana="minor",
        suit=suit_id,
        rank=rank_id,
        keywords_ru=suit["kw_ru"],
        keywords_en=suit["kw_en"],
        meanings={
            "ru": {"upright": ru_upr, "reversed": ru_rev},
            "en": {"upright": en_upr, "reversed": en_rev},
        },
        ru=LocalizedCard(
            upright=CardMeanings(essence=ru_upr, keywords=suit["kw_ru"]),
            reversed=CardMeanings(essence=ru_rev, keywords=suit["kw_ru"]),
        ),
        en=LocalizedCard(
            upright=CardMeanings(essence=en_upr, keywords=suit["kw_en"]),
            reversed=CardMeanings(essence=en_rev, keywords=suit["kw_en"]),
        ),
    )


def build_deck() -> list[TarotCard]:
    deck: list[TarotCard] = []

    for m in MAJOR:
        deck.append(_build_major(m))

    for suit_id, suit in SUITS.items():
        for rank_id in RANK_NAMES_RU:
            variants = RANK_SUIT_VARIANTS.get(rank_id, {}).get(suit_id, {})
            ru_upr = variants.get("ru_upr", "").format(theme=suit["ru_theme"])
            ru_rev = variants.get("ru_rev", "").format(theme=suit["ru_theme"])
            en_upr = variants.get("en_upr", "").format(theme=suit["en_theme"])
            en_rev = variants.get("en_rev", "").format(theme=suit["en_theme"])
            deck.append(_build_minor(
                suit_id, suit, rank_id,
                RANK_NAMES_RU[rank_id], RANK_NAMES_EN[rank_id],
                ru_upr, ru_rev, en_upr, en_rev,
            ))
        for court_id in COURT_NAMES_RU:
            variants = COURT_SUIT_VARIANTS.get(court_id, {}).get(suit_id, {})
            ru_upr = variants.get("ru_upr", "").format(theme=suit["ru_theme"])
            ru_rev = variants.get("ru_rev", "").format(theme=suit["ru_theme"])
            en_upr = variants.get("en_upr", "").format(theme=suit["en_theme"])
            en_rev = variants.get("en_rev", "").format(theme=suit["en_theme"])
            deck.append(_build_minor(
                suit_id, suit, court_id,
                COURT_NAMES_RU[court_id], COURT_NAMES_EN[court_id],
                ru_upr, ru_rev, en_upr, en_rev,
            ))
    return deck
