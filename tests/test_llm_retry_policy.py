"""Tests for the bounded, privacy-safe LLM retry policy."""
from __future__ import annotations

import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.llm.adapter import (  # noqa: E402
    _error_category,
    _new_request_id,
    _should_retry_exception,
    _timeout_stage,
)


class ProviderError(Exception):
    def __init__(self, status_code: int, message: str = "provider error") -> None:
        self.status_code = status_code
        super().__init__(message)


@pytest.mark.parametrize(
    ("exc", "category", "retry"),
    [
        (ProviderError(401), "auth", False),
        (ProviderError(403), "auth", False),
        (ProviderError(429), "rate_limit", True),
        (ProviderError(500), "provider_server", True),
        (ProviderError(400), "provider_client", False),
        (asyncio.TimeoutError(), "timeout", True),
        (ConnectionError("connection dropped"), "network", True),
        (json.JSONDecodeError("bad JSON", "{", 1), "validation", True),
        (ValueError("share_summary contains private fragment"), "privacy", True),
        (RuntimeError("unexpected failure"), "unknown", False),
    ],
)
def test_error_taxonomy_is_bounded_and_explicit(exc: Exception, category: str, retry: bool) -> None:
    assert _error_category(exc) == category
    assert _should_retry_exception(exc) is retry


def test_timeout_stage_does_not_persist_error_text() -> None:
    assert _timeout_stage(asyncio.TimeoutError("private question must never leak")) == "total"
    assert _timeout_stage(ProviderError(500)) is None


def test_request_id_is_opaque_and_does_not_embed_user_data() -> None:
    request_id = _new_request_id()
    assert len(request_id) == 32
    assert int(request_id, 16) >= 0
    assert "user" not in request_id


def test_retry_policy_retries_rate_limit_once_then_succeeds() -> None:
    from types import SimpleNamespace

    from bot.llm.adapter import _retry_policy

    async def run() -> int:
        calls = 0
        async for attempt in _retry_policy(SimpleNamespace(llm_v2_max_attempts=2)):
            with attempt:
                calls += 1
                if calls == 1:
                    raise ProviderError(429)
        return calls

    assert asyncio.run(run()) == 2


def test_retry_policy_does_not_retry_auth_error() -> None:
    from types import SimpleNamespace

    from bot.llm.adapter import _retry_policy

    async def run() -> int:
        calls = 0
        async for attempt in _retry_policy(SimpleNamespace(llm_v2_max_attempts=2)):
            with attempt:
                calls += 1
                raise ProviderError(401)
        return calls

    with pytest.raises(ProviderError):
        asyncio.run(run())


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
        from types import SimpleNamespace

        self.completions = FakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


def _valid_completion(drawn) -> object:
    from types import SimpleNamespace

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
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=22),
    )


def test_v2_path_retries_once_uses_backup_and_persists_safe_usage(tmp_path) -> None:
    from dataclasses import replace

    from sqlalchemy import select

    from bot.config import load_config
    from bot.db.database import close_db, get_session, init_db
    from bot.db.models import LlmUsage
    from bot.llm.adapter import _interpret_reading_v2
    from bot.tarot import draw

    async def run() -> None:
        cfg = replace(
            load_config(require_token=False),
            openrouter_api_key="test-key",
            llm_retry_policy_v2=True,
            llm_model="primary-model",
            llm_backup_model="backup-model",
            db_path=str(tmp_path / "moira-v2-success.db"),
        )
        await init_db(cfg.db_path)
        drawn = draw("situation")
        client = FakeClient([ProviderError(429), _valid_completion(drawn)])
        result, generation_id = await _interpret_reading_v2(
            cfg,
            client,
            provider="provider.example",
            lang="ru",
            question="private question must not be persisted",
            memory="",
            drawn=drawn,
            user_id=42,
            spread_id="situation",
            messages=[{"role": "system", "content": "contract"}],
        )

        assert result is not None
        assert len(client.completions.calls) == 2
        assert client.completions.calls[0]["model"] == "primary-model"
        assert client.completions.calls[1]["model"] == "backup-model"
        async with get_session() as session:
            usage = (await session.execute(select(LlmUsage))).scalar_one()
        assert usage.provider == "provider.example"
        assert usage.model == "backup-model"
        assert usage.attempts == 2
        assert usage.fallback_used is False
        assert usage.error_category is None
        assert usage.request_id and len(usage.request_id) == 32
        assert "private question" not in str(usage.__dict__)
        await close_db()

    asyncio.run(run())


def test_v2_path_does_not_retry_auth_and_records_controlled_fallback(tmp_path) -> None:
    from dataclasses import replace

    from sqlalchemy import select

    from bot.config import load_config
    from bot.db.database import close_db, get_session, init_db
    from bot.db.models import LlmUsage
    from bot.llm.adapter import _interpret_reading_v2
    from bot.tarot import draw

    async def run() -> None:
        cfg = replace(
            load_config(require_token=False),
            openrouter_api_key="test-key",
            llm_retry_policy_v2=True,
            db_path=str(tmp_path / "moira-v2-auth.db"),
        )
        await init_db(cfg.db_path)
        client = FakeClient([ProviderError(401, "authentication failed")])
        result, generation_id = await _interpret_reading_v2(
            cfg,
            client,
            provider="provider.example",
            lang="ru",
            question="private question must not be persisted",
            memory="",
            drawn=draw("situation"),
            user_id=43,
            spread_id="situation",
            messages=[{"role": "system", "content": "contract"}],
        )

        assert result is None
        assert len(client.completions.calls) == 1
        async with get_session() as session:
            usage = (await session.execute(select(LlmUsage))).scalar_one()
        assert usage.status == "fallback"
        assert usage.attempts == 1
        assert usage.fallback_used is True
        assert usage.error_category == "auth"
        assert usage.timeout_stage is None
        assert "private question" not in str(usage.__dict__)
        await close_db()

    asyncio.run(run())


def test_interpret_reading_selects_v2_path_only_when_feature_flag_enabled(tmp_path, monkeypatch) -> None:
    from dataclasses import replace

    import openai

    from bot.config import load_config
    from bot.db.database import close_db, init_db
    from bot.llm import adapter
    from bot.tarot import draw

    async def run() -> None:
        cfg = replace(
            load_config(require_token=False),
            openrouter_api_key="test-key",
            llm_retry_policy_v2=True,
            db_path=str(tmp_path / "moira-v2-entrypoint.db"),
        )
        await init_db(cfg.db_path)
        drawn = draw("situation")
        client = FakeClient([_valid_completion(drawn)])
        captured: dict = {}

        def fake_client_factory(**kwargs):
            captured.update(kwargs)
            return client

        monkeypatch.setattr(openai, "AsyncOpenAI", fake_client_factory)
        result, _gid = await adapter.interpret_reading(
            cfg,
            "ru",
            "Расклад «Ситуация»",
            None,
            drawn,
            user_id=44,
            spread_id="situation",
        )

        assert result is not None
        assert captured["timeout"] == cfg.llm_v2_primary_timeout_sec
        assert len(client.completions.calls) == 1
        await close_db()

    asyncio.run(run())


def test_provider_telemetry_strips_url_credentials_and_path() -> None:
    from bot.llm.adapter import _provider_from_url

    assert _provider_from_url("https://secret-user:secret-pass@provider.example/v1") == "provider.example"
