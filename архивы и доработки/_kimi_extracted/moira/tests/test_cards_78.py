"""Validate that all 78 tarot cards have complete RU/EN content."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.tarot.deck import build_deck
from bot.visual.assets import card_image_path


def test_seventy_eight_cards() -> None:
    deck = build_deck()
    assert len(deck) == 78, f"Expected 78 cards, got {len(deck)}"


def test_unique_ids() -> None:
    deck = build_deck()
    ids = [c.id for c in deck]
    assert len(set(ids)) == 78, f"Duplicate IDs found: {len(ids) - len(set(ids))}"


def test_all_have_ru_and_en() -> None:
    deck = build_deck()
    for c in deck:
        assert c.ru.upright.essence, f"{c.id}: missing RU upright essence"
        assert c.ru.reversed.essence, f"{c.id}: missing RU reversed essence"
        assert c.en.upright.essence, f"{c.id}: missing EN upright essence"
        assert c.en.reversed.essence, f"{c.id}: missing EN reversed essence"


def test_all_have_keywords() -> None:
    deck = build_deck()
    for c in deck:
        assert c.keywords_ru, f"{c.id}: missing RU keywords"
        assert c.keywords_en, f"{c.id}: missing EN keywords"


def test_major_have_symbols() -> None:
    deck = build_deck()
    for c in deck:
        if c.arcana == "major":
            assert c.ru.symbols, f"{c.id}: missing RU symbols"
            assert c.en.symbols, f"{c.id}: missing EN symbols"
            assert c.ru.reflection_question, f"{c.id}: missing RU reflection"
            assert c.en.reflection_question, f"{c.id}: missing EN reflection"


def test_no_empty_meanings() -> None:
    deck = build_deck()
    for c in deck:
        for lang in ("ru", "en"):
            m = c.meanings.get(lang)
            assert m, f"{c.id}: missing meanings for {lang}"
            assert m.get("upright"), f"{c.id}: missing upright for {lang}"
            assert m.get("reversed"), f"{c.id}: missing reversed for {lang}"


def test_upright_differs_from_reversed() -> None:
    deck = build_deck()
    for c in deck:
        for lang in ("ru", "en"):
            up = c.meanings[lang]["upright"]
            rev = c.meanings[lang]["reversed"]
            assert up != rev, f"{c.id} {lang}: upright == reversed"


def test_all_assets_exist() -> None:
    deck = build_deck()
    missing = []
    for c in deck:
        if card_image_path(c) is None:
            missing.append(c.id)
    assert not missing, f"Missing assets: {missing}"


def test_major_arcana_count() -> None:
    deck = build_deck()
    major = [c for c in deck if c.arcana == "major"]
    assert len(major) == 22, f"Expected 22 Major Arcana, got {len(major)}"


def test_minor_arcana_count() -> None:
    deck = build_deck()
    minor = [c for c in deck if c.arcana == "minor"]
    assert len(minor) == 56, f"Expected 56 Minor Arcana, got {len(minor)}"


def run_all() -> None:
    tests = [
        test_seventy_eight_cards,
        test_unique_ids,
        test_all_have_ru_and_en,
        test_all_have_keywords,
        test_major_have_symbols,
        test_no_empty_meanings,
        test_upright_differs_from_reversed,
        test_all_assets_exist,
        test_major_arcana_count,
        test_minor_arcana_count,
    ]
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__} — {e}")
            raise
    print("\nALL CARD VALIDATION TESTS PASSED")


if __name__ == "__main__":
    run_all()
