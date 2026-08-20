"""Block 5: LLM schema length & semantic validators (bot/llm/adapter.py).

Covers the reading length table (headline<=90, opening 60-240, per-card 40-420,
synthesis 180-650, practical_focus 60-260, reflection<=220, voice 140-450,
share 60-240), the "voice_summary is not a copy of synthesis" rule, and the
share_summary privacy guard (no user question inside).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pydantic import ValidationError

from bot.llm.adapter import (
    FORMAT_EN,
    FORMAT_RU,
    TarotReadingResult,
    assert_share_summary_privacy,
    parse_reading_json,
)


def _pad(base: str, min_len: int, max_len: int) -> str:
    """Repeat base until >= min_len, then hard-cap at max_len."""
    while len(base) < min_len:
        base = base + " " + base
    return base[:max_len]


def _valid(**overrides) -> TarotReadingResult:
    data = {
        "headline": "Трактовка расклада на сегодня",
        "opening": _pad("Карты открывают ситуацию с трёх сторон.", 80, 180),
        "card_interpretations": [
            {"position": "Суть", "card_name": "Шут", "orientation": "upright",
             "core_message": _pad("Новое начало и доверие жизни: шаг в неизвестность.", 170, 420),
             "symbolic_detail": "Белый пёс у ног", "context_connection": "Работа"}
        ],
        "synthesis": _pad("Синтез расклада: карты показывают динамику, а не итог.", 320, 600),
        "practical_focus": _pad("Сфокусируйтесь на первом шаге и доверьтесь процессу.", 100, 220),
        "reflection_question": "Что мешает сделать первый шаг?",
        "voice_summary": _pad("Устная версия: карты говорят о начале пути.", 220, 420),
        "share_summary": _pad("Краткий итог для пересылки: начало нового пути.", 100, 220),
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


def test_opening_range_60_240() -> None:
    with pytest.raises(ValidationError):
        _valid(opening="too short")
    with pytest.raises(ValidationError):
        _valid(opening="x" * 241)


def test_card_interpretation_range_40_420() -> None:
    with pytest.raises(ValidationError):
        _valid(card_interpretations=_card("short"))
    with pytest.raises(ValidationError):
        _valid(card_interpretations=_card("x" * 421))


def test_synthesis_range_180_650() -> None:
    with pytest.raises(ValidationError):
        _valid(synthesis="short")
    with pytest.raises(ValidationError):
        _valid(synthesis="x" * 651)


def test_practical_focus_range_60_260() -> None:
    with pytest.raises(ValidationError):
        _valid(practical_focus="short")
    with pytest.raises(ValidationError):
        _valid(practical_focus="x" * 261)


def test_reflection_question_max_220() -> None:
    with pytest.raises(ValidationError):
        _valid(reflection_question="x" * 221)


def test_reflection_question_must_end_with_question_mark() -> None:
    with pytest.raises(ValidationError, match="must end with a question mark"):
        _valid(reflection_question="Сделайте один наблюдаемый шаг.")
    with pytest.raises(ValidationError, match="must end with a question mark"):
        _valid(reflection_question="Choose one observable next step.")

    result = _valid(reflection_question="Что можно проверить следующим шагом?   ")
    assert result.reflection_question


def test_reflection_question_contract_is_explicit_in_both_languages() -> None:
    assert "reflection_question" in FORMAT_RU
    assert "заканчиваться знаком «?»" in FORMAT_RU
    assert "reflection_question" in FORMAT_EN
    assert 'must end with "?"' in FORMAT_EN


def test_voice_summary_range_140_450() -> None:
    with pytest.raises(ValidationError):
        _valid(voice_summary="short")
    with pytest.raises(ValidationError):
        _valid(voice_summary="x" * 451)


def test_share_summary_range_60_240() -> None:
    with pytest.raises(ValidationError):
        _valid(share_summary="short")
    with pytest.raises(ValidationError):
        _valid(share_summary="x" * 241)


def test_voice_summary_must_not_copy_synthesis() -> None:
    same = _pad("Одинаковый текст для проверки.", 320, 420)
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


def test_share_summary_privacy_rejects_exact_recent_reading_memory() -> None:
    memory = "Недавняя трактовка описывает личную ситуацию человека и её детали."
    leak = _pad(f"Итог: {memory} Карты предлагают наблюдать за ходом событий.", 180, 300)

    with pytest.raises(ValueError, match="recent-reading context"):
        assert_share_summary_privacy(leak, None, memory)

    assert_share_summary_privacy(_pad("Итог о текущих картах без прошлого контекста.", 180, 300), None, memory) is None


def test_parse_reading_json_accepts_plain_and_fenced_json() -> None:
    raw = _valid().model_dump_json()
    assert parse_reading_json(raw).headline == "Трактовка расклада на сегодня"
    assert parse_reading_json(f"```json\n{raw}\n```").headline == "Трактовка расклада на сегодня"


def test_parse_reading_json_clips_provider_overflow_at_word_boundary() -> None:
    payload = _valid().model_dump()
    payload["opening"] = "Слово " * 50
    payload["card_interpretations"][0]["core_message"] = "Слово " * 100
    payload["card_interpretations"][0]["symbolic_detail"] = "Символ " * 50
    payload["card_interpretations"][0]["context_connection"] = "Контекст " * 50
    result = parse_reading_json(json.dumps(payload, ensure_ascii=False))

    assert len(result.opening) <= 240
    assert result.opening.endswith("…")
    assert len(result.card_interpretations[0].core_message) <= 420
    assert len(result.card_interpretations[0].symbolic_detail) <= 200
    assert len(result.card_interpretations[0].context_connection) <= 200
