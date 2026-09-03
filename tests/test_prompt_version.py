"""QW-2.5: PROMPT_VERSION is config-overridable and logged on every LLM call."""
from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import replace
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from bot.config import load_config
from bot.db.database import close_db, get_session, init_db
from bot.db.models import LlmUsage
from bot.llm import adapter
from bot.llm.adapter import PROMPT_VERSION, resolve_prompt_version
from bot.tarot import draw


class ProviderError(Exception):
    def __init__(self, status_code: int, message: str = "provider error") -> None:
        self.status_code = status_code
        super().__init__(message)


class FakeCompletions:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)

    async def create(self, **kwargs):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses: list[object]) -> None:
        completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=completions)


def _completion_for(drawn) -> object:
    from bot.llm.adapter import TarotReadingResult

    def pad(text: str, minimum: int, maximum: int) -> str:
        while len(text) < minimum:
            text = f"{text} {text}"
        return text[:maximum]

    payload = TarotReadingResult(
        headline="Точный и спокойный ответ",
        opening=pad("Карты открывают спокойную динамику и ясный фокус.", 80, 180),
        card_interpretations=[
            {
                "position": card.position_label["ru"],
                "card_name": card.card.name("ru"),
                "orientation": "reversed" if card.reversed else "upright",
                "core_message": pad("Эта карта показывает конкретное напряжение и полезный следующий шаг.", 120, 300),
                "symbolic_detail": "",
                "context_connection": "",
            }
            for card in drawn
        ],
        synthesis=pad("Синтез объединяет карты в одну практическую линию без обещаний и предсказаний.", 240, 500),
        practical_focus=pad("Выберите один небольшой проверяемый шаг и выполните его в ближайшее время.", 100, 220),
        reflection_question="Что поможет сделать этот небольшой шаг сегодня?",
        voice_summary=pad("Устная версия удерживает главную линию расклада и предлагает спокойно выбрать следующий шаг.", 180, 380),
        share_summary=pad("Карты предлагают увидеть главное напряжение, выбрать ясный фокус и двигаться небольшим шагом.", 100, 220),
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=payload.model_dump_json()))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2),
    )


def _raw_completion(content: str) -> object:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2),
    )


def test_default_prompt_version_unchanged(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROMPT_VERSION", raising=False)
    assert PROMPT_VERSION == "v6-mystical-clear"
    cfg = load_config(require_token=False)
    assert cfg.llm_prompt_version == "v6-mystical-clear"
    assert resolve_prompt_version(cfg) == "v6-mystical-clear"


def test_env_override_is_picked_up(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROMPT_VERSION", "v9-test-override")
    cfg = load_config(require_token=False)
    assert cfg.llm_prompt_version == "v9-test-override"
    assert resolve_prompt_version(cfg) == "v9-test-override"


def test_custom_version_reaches_usage_on_success_and_fallback(tmp_path, monkeypatch) -> None:
    import openai

    async def run() -> None:
        # Legacy success path.
        cfg = replace(
            load_config(require_token=False),
            openrouter_api_key="test-key",
            llm_prompt_version="v9-test",
            db_path=str(tmp_path / "moira-pv-ok.db"),
        )
        await init_db(cfg.db_path)
        drawn = draw("situation")
        monkeypatch.setattr(openai, "AsyncOpenAI", lambda **kwargs: FakeClient([_completion_for(drawn)]))
        result, _gid = await adapter.interpret_reading(
            cfg, "ru", "Расклад «Ситуация»", None, drawn, user_id=1, spread_id="situation"
        )
        assert result is not None
        async with get_session() as session:
            usage = (await session.execute(select(LlmUsage))).scalar_one()
            assert usage.prompt_version == "v9-test"
        await close_db()

        # V2 fallback path (auth error → no retry).
        cfg2 = replace(cfg, llm_retry_policy_v2=True, db_path=str(tmp_path / "moira-pv-fb.db"))
        await init_db(cfg2.db_path)
        monkeypatch.setattr(openai, "AsyncOpenAI", lambda **kwargs: FakeClient([ProviderError(401)]))
        result2, _gid2 = await adapter.interpret_reading(
            cfg2, "ru", "Расклад «Ситуация»", None, drawn, user_id=1, spread_id="situation"
        )
        assert result2 is None
        async with get_session() as session:
            usage2 = (await session.execute(select(LlmUsage))).scalar_one()
            assert usage2.status == "fallback"
            assert usage2.prompt_version == "v9-test"
        await close_db()

    asyncio.run(run())


def test_custom_version_reaches_usage_on_repair(tmp_path) -> None:
    async def run() -> None:
        cfg = replace(
            load_config(require_token=False),
            openrouter_api_key="test-key",
            llm_retry_policy_v2=True,
            llm_controlled_repair_enabled=True,
            llm_prompt_version="v9-test",
            db_path=str(tmp_path / "moira-pv-repair.db"),
        )
        await init_db(cfg.db_path)
        drawn = draw("situation")
        client = FakeClient([_raw_completion("not json"), _completion_for(drawn)])
        result, _gid = await adapter._interpret_reading_v2(
            cfg, client, provider="provider.example", lang="ru", question=None,
            memory="", drawn=drawn, user_id=3, spread_id="situation",
            messages=[{"role": "user", "content": "contract"}],
        )
        assert result is not None
        async with get_session() as session:
            usage = (await session.execute(select(LlmUsage))).scalar_one()
            assert usage.repair_used is True
            assert usage.prompt_version == "v9-test"
        await close_db()

    asyncio.run(run())
