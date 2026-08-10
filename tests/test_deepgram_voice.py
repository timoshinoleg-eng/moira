from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot.keyboards import question_input_kb, voice_transcript_kb
from bot.voice.transcribe import DeepgramTranscriber, VoiceTranscriptionError, parse_transcription


ROOT = Path(__file__).resolve().parents[1]


def _callbacks(keyboard) -> set[str]:
    return {
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data
    }


def test_voice_keyboard_keeps_spread_context_and_editable_confirmation() -> None:
    assert "voice:start:love" in _callbacks(question_input_kb("en", "love"))
    assert {"voice:confirm", "voice:edit", "voice:repeat", "voice:cancel"} <= _callbacks(
        voice_transcript_kb("ru")
    )


def test_voice_copy_has_ru_en_parity_and_viral_caption() -> None:
    ru = json.loads((ROOT / "bot" / "i18n" / "locales" / "ru.json").read_text(encoding="utf-8"))
    en = json.loads((ROOT / "bot" / "i18n" / "locales" / "en.json").read_text(encoding="utf-8"))
    keys = {
        "btn_voice_question",
        "btn_voice_consent",
        "btn_text_instead",
        "btn_voice_confirm",
        "btn_voice_edit",
        "btn_voice_repeat",
        "voice_consent_short",
        "voice_ready",
        "voice_transcript",
        "voice_transcription_failed",
        "share_caption_voice",
    }
    assert keys <= ru.keys()
    assert keys <= en.keys()
    assert "голос" in ru["share_caption_voice"].lower()
    assert "out loud" in en["share_caption_voice"].lower()


def test_parse_transcription_rejects_empty_output() -> None:
    with pytest.raises(VoiceTranscriptionError, match="empty_transcript"):
        parse_transcription({"results": {"channels": [{"alternatives": [{"transcript": "  "}]}]}})


def test_deepgram_transcriber_uses_completed_audio_and_explicit_language() -> None:
    async def run() -> None:
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["auth"] = request.headers["Authorization"]
            seen["content_type"] = request.headers["Content-Type"]
            seen["body"] = request.content
            return httpx.Response(
                200,
                json={
                    "metadata": {"duration": 4.2},
                    "results": {"channels": [{"alternatives": [{"transcript": "Что выбрать?", "confidence": 0.96}]}]},
                },
            )

        transcript = await DeepgramTranscriber(
            "test-key",
            transport=httpx.MockTransport(handler),
        ).transcribe(b"ogg-bytes", language="ru", content_type="audio/ogg")
        assert transcript.text == "Что выбрать?"
        assert transcript.duration_sec == 4.2
        assert "model=nova-3" in seen["url"]
        assert "language=ru" in seen["url"]
        assert seen["auth"] == "Token test-key"
        assert seen["content_type"] == "audio/ogg"
        assert seen["body"] == b"ogg-bytes"

    asyncio.run(run())


def test_deepgram_rate_limit_becomes_a_user_safe_category() -> None:
    async def run() -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"message": "busy"})

        client = DeepgramTranscriber("test-key", transport=httpx.MockTransport(handler))
        with pytest.raises(VoiceTranscriptionError, match="provider_busy"):
            await client.transcribe(b"audio", language="en", content_type="audio/ogg")

    asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
