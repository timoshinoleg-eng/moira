"""Regression tests for the opt-in, privacy-safe controlled repair path."""
from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import replace
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import load_config
from bot.db.database import close_db, init_db
from bot.llm.adapter import _build_controlled_repair_messages, _interpret_reading_v2
from bot.tarot import draw


class ProviderError(Exception):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"provider status {status_code}")


class FakeCompletions:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses: list[object]) -> None:
        self.completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def _completion_for(drawn) -> object:
    from bot.llm.adapter import TarotReadingResult

    def pad(value: str, minimum: int, maximum: int) -> str:
        while len(value) < minimum:
            value = f"{value} {value}"
        return value[:maximum]

    reading = TarotReadingResult(
        headline="Спокойная линия расклада",
        opening=pad("Карты показывают спокойное движение и предлагают ясный фокус.", 80, 180),
        card_interpretations=[
            {
                "position": card.position_label["ru"],
                "card_name": card.card.name("ru"),
                "orientation": "reversed" if card.reversed else "upright",
                "core_message": pad("Карта показывает напряжение этой позиции и помогает выбрать реалистичный следующий шаг.", 120, 300),
                "symbolic_detail": "",
                "context_connection": "",
            }
            for card in drawn
        ],
        synthesis=pad("Синтез расклада связывает карты в одну практическую линию и не даёт гарантий будущего.", 240, 500),
        practical_focus=pad("Сделайте один небольшой шаг, который можно проверить в ближайшее время.", 100, 220),
        reflection_question="Какой следующий шаг сейчас действительно доступен?",
        voice_summary=pad("Устная версия сохраняет главный смысл карт и спокойно возвращает человеку право выбора.", 180, 380),
        share_summary=pad("Карты предлагают увидеть главный фокус, выбрать посильный шаг и двигаться без лишней спешки.", 100, 220),
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=reading.model_dump_json()))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20),
    )


def _raw_completion(content: str) -> object:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20),
    )


def test_repair_messages_exclude_private_context_and_raw_output() -> None:
    drawn = draw("situation")
    messages = _build_controlled_repair_messages("ru", "situation", drawn, "validation")
    visible = "\n".join(message["content"] for message in messages)

    assert "TOP_SECRET_QUESTION" not in visible
    assert "TOP_SECRET_MEMORY" not in visible
    assert "TOP_SECRET_RAW_OUTPUT" not in visible
    assert "Категория локальной проверки: validation" in visible
    for card in drawn:
        assert card.card.name("ru") in visible


def test_controlled_repair_uses_safe_second_payload_and_never_exceeds_two_calls(tmp_path) -> None:
    async def run() -> None:
        cfg = replace(
            load_config(require_token=False),
            openrouter_api_key="test-key",
            llm_retry_policy_v2=True,
            llm_controlled_repair_enabled=True,
            llm_model="primary-model",
            llm_backup_model="backup-model",
            db_path=str(tmp_path / "repair.db"),
        )
        await init_db(cfg.db_path)
        drawn = draw("situation")
        question = "TOP_SECRET_QUESTION"
        memory = "TOP_SECRET_MEMORY"
        client = FakeClient([_raw_completion("TOP_SECRET_RAW_OUTPUT not JSON"), _completion_for(drawn)])

        result, generation_id = await _interpret_reading_v2(
            cfg,
            client,
            provider="provider.example",
            lang="ru",
            question=question,
            memory=memory,
            drawn=drawn,
            user_id=1,
            spread_id="situation",
            messages=[
                {"role": "system", "content": "system contract"},
                {"role": "user", "content": f"question={question}; memory={memory}"},
            ],
        )

        assert result is not None
        assert len(client.completions.calls) == 2
        assert client.completions.calls[0]["model"] == "primary-model"
        assert client.completions.calls[1]["model"] == "backup-model"
        repair_payload = "\n".join(message["content"] for message in client.completions.calls[1]["messages"])
        assert question not in repair_payload
        assert memory not in repair_payload
        assert "TOP_SECRET_RAW_OUTPUT" not in repair_payload
        await close_db()

    asyncio.run(run())


def test_transient_error_keeps_normal_retry_payload_when_repair_is_enabled(tmp_path) -> None:
    async def run() -> None:
        cfg = replace(
            load_config(require_token=False),
            openrouter_api_key="test-key",
            llm_retry_policy_v2=True,
            llm_controlled_repair_enabled=True,
            db_path=str(tmp_path / "repair-transient.db"),
        )
        await init_db(cfg.db_path)
        drawn = draw("situation")
        client = FakeClient([ProviderError(429), _completion_for(drawn)])
        normal_messages = [{"role": "user", "content": "TOP_SECRET_QUESTION"}]

        result, generation_id = await _interpret_reading_v2(
            cfg,
            client,
            provider="provider.example",
            lang="ru",
            question=None,
            memory="",
            drawn=drawn,
            user_id=2,
            spread_id="situation",
            messages=normal_messages,
        )

        assert result is not None
        assert len(client.completions.calls) == 2
        assert client.completions.calls[1]["messages"] == normal_messages
        await close_db()

    asyncio.run(run())
