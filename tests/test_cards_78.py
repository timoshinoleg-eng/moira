"""Validate that all 78 tarot cards have complete RU/EN content."""
from __future__ import annotations

import os
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

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


def test_all_runtime_light_shadow_advice_are_complete_and_not_placeholders() -> None:
    forbidden = ("todo", "tbd", "placeholder", "заполнить позже")
    for card in build_deck():
        for lang in ("ru", "en"):
            for orientation in (card.localized(lang).upright, card.localized(lang).reversed):
                for field in ("essence", "light", "shadow", "advice"):
                    value = getattr(orientation, field)
                    assert value.strip(), f"{card.id} {lang} {field}: empty"
                    assert not any(mark in value.lower() for mark in forbidden), (
                        f"{card.id} {lang} {field}: placeholder text"
                    )


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


def test_assets_are_readable_unique_and_manifested() -> None:
    deck = build_deck()
    cards_dir = Path(__file__).resolve().parents[1] / "assets" / "cards"
    manifest = json.loads((cards_dir / "manifest.json").read_text(encoding="utf-8"))
    entries = manifest["cards"]
    assert len(entries) == 78
    assert {entry["card_id"] for entry in entries} == {card.id for card in deck}
    assert len({entry["local_filename"] for entry in entries}) == 78
    assert len({entry["sha256"] for entry in entries}) == 78
    assert len({entry["source_sha1"] for entry in entries}) == 78
    for entry in entries:
        path = cards_dir / entry["local_filename"]
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            assert image.size == (350, 600)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


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
        test_all_runtime_light_shadow_advice_are_complete_and_not_placeholders,
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
