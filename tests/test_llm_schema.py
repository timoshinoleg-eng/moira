"""Block 5: LLM schema length & semantic validators (bot/llm/adapter.py).

Covers the ТЗ length table (headline<=90, opening 120-250, per-card 300-550,
synthesis 500-900, practical_focus 180-350, reflection<=220, voice 500-800,
share 180-300), the "voice_summary is not a copy of synthesis" rule, and the
share_summary privacy guard (no user question inside).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pydantic import ValidationError

from bot.llm.adapter import TarotReadingResult, assert_share_summary_privacy


def _pad(base: str, min_len: int, max_len: int) -> str:
    """Repeat base until >= min_len, then hard-cap at max_len."""
    while len(base) < min_len:
        base = base + " " + base
    return base[:max_len]


def _valid(**overrides) -> TarotReadingResult:
    data = {
        "headline": "Трактовка расклада на сегодня",
        "opening": _pad("Карты открывают ситуацию с трёх сторон.", 120, 250),
        "card_interpretations": [
            {"position": "Суть", "card_name": "Шут", "orientation": "upright",
             "core_message": _pad("Новое начало и доверие жизни: шаг в неизвестность.", 300, 550),
             "symbolic_detail": "Белый пёс у ног", "context_connection": "Работа"}
        ],
        "synthesis": _pad("Синтез расклада: карты показывают динамику, а не итог.", 500, 900),
        "practical_focus": _pad("Сфокусируйтесь на первом шаге и доверьтесь процессу.", 180, 350),
        "reflection_question": "Что мешает сделать первый шаг?",
        "voice_summary": _pad("Устная версия: карты говорят о начале пути.", 500, 800),
        "share_summary": _pad("Краткий итог для пересылки: начало нового пути.", 180, 300),
    }
    data.update(overrides)
    return TarotReadingResult(**data)


def _card(core_message: str) -> list[dict]:
    return [{"position": "Суть", "card_name": "Шут", "orientation": "upright",
             "core_message": core_message, "symbolic_detail": "", "context_connection": ""}]


def test_valid_instance_passes() -> None:
    r = _valid()
    assert r.voice_summary != r.synthesis


def test_headline_max_90() -> None:
    with pytest.raises(ValidationError):
        _valid(headline="x" * 91)


def test_opening_range_120_250() -> None:
    with pytest.raises(ValidationError):
        _valid(opening="too short")
    with pytest.raises(ValidationError):
        _valid(opening="x" * 251)


def test_card_interpretation_range_300_550() -> None:
    with pytest.raises(ValidationError):
        _valid(card_interpretations=_card("short"))
    with pytest.raises(ValidationError):
        _valid(card_interpretations=_card("x" * 551))


def test_synthesis_range_500_900() -> None:
    with pytest.raises(ValidationError):
        _valid(synthesis="short")
    with pytest.raises(ValidationError):
        _valid(synthesis="x" * 901)


def test_practical_focus_range_180_350() -> None:
    with pytest.raises(ValidationError):
        _valid(practical_focus="short")
    with pytest.raises(ValidationError):
        _valid(practical_focus="x" * 351)


def test_reflection_question_max_220() -> None:
    with pytest.raises(ValidationError):
        _valid(reflection_question="x" * 221)


def test_voice_summary_range_500_800() -> None:
    with pytest.raises(ValidationError):
        _valid(voice_summary="short")
    with pytest.raises(ValidationError):
        _valid(voice_summary="x" * 801)


def test_share_summary_range_180_300() -> None:
    with pytest.raises(ValidationError):
        _valid(share_summary="short")
    with pytest.raises(ValidationError):
        _valid(share_summary="x" * 301)


def test_voice_summary_must_not_copy_synthesis() -> None:
    same = _pad("Одинаковый текст для проверки.", 500, 800)
    with pytest.raises(ValidationError):
        _valid(voice_summary=same, synthesis=same)


def test_share_summary_privacy() -> None:
    question = "Любит ли он меня?"
    leak = _pad(f"Итог: {question} карты говорят о чувствах.", 180, 300)
    with pytest.raises(ValueError):
        assert_share_summary_privacy(leak, question)
    # clean cases must pass
    assert_share_summary_privacy(_pad("Итог без упоминания вопроса.", 180, 300), question) is None
    assert_share_summary_privacy(_pad("Итог без вопроса.", 180, 300), None) is None
    assert_share_summary_privacy(_pad("Итог без вопроса.", 180, 300), "-") is None
