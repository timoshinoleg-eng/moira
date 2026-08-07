"""Patch 1 regression tests: FSM birth flow, paywall i18n, voice fallback."""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DB_PATH", os.path.join(tempfile.gettempdir(), "moira_patch1.db"))

from aiogram.exceptions import TelegramBadRequest

from bot.handlers.features import _parse_birth_date
from bot.i18n import t
from bot.keyboards import paywall_kb


class FakeMessage:
    def __init__(self, raise_voice: Exception | None = None, raise_audio: Exception | None = None) -> None:
        self.calls: list[str] = []
        self.raise_voice = raise_voice
        self.raise_audio = raise_audio
        self.from_user = type("User", (), {"id": 123456})()

    async def answer_voice(self, *args, **kwargs):
        self.calls.append("answer_voice")
        if self.raise_voice:
            raise self.raise_voice
        return None

    async def answer_audio(self, *args, **kwargs):
        self.calls.append("answer_audio")
        if self.raise_audio:
            raise self.raise_audio
        return None

    async def answer(self, *args, **kwargs):
        self.calls.append("answer")
        return None


async def _test_voice_fallback() -> None:
    from bot.handlers.reading import _send_voice_or_audio

    # 1. voice succeeds
    msg = FakeMessage()
    await _send_voice_or_audio(msg, b"audio", "ru")
    assert msg.calls == ["answer_voice"], f"expected voice first, got {msg.calls}"

    # 2. voice forbidden -> audio fallback succeeds
    msg = FakeMessage(raise_voice=TelegramBadRequest(method="sendVoice", message="VOICE_MESSAGES_FORBIDDEN"))
    await _send_voice_or_audio(msg, b"audio", "en")
    assert msg.calls == ["answer_voice", "answer_audio"], f"expected voice+audio, got {msg.calls}"

    # 3. voice and audio both fail -> localized notice
    msg = FakeMessage(
        raise_voice=TelegramBadRequest(method="sendVoice", message="VOICE_MESSAGES_FORBIDDEN"),
        raise_audio=TelegramBadRequest(method="sendAudio", message="whatever"),
    )
    await _send_voice_or_audio(msg, b"audio", "ru")
    assert "answer" in msg.calls, f"expected text notice after audio failure, got {msg.calls}"


async def _test_paywall_i18n() -> None:
    for lang in ("ru", "en"):
        kb = paywall_kb(lang)
        assert kb.inline_keyboard, f"paywall_kb({lang}) is empty"
        texts = [btn.text for row in kb.inline_keyboard for btn in row]
        for text in texts:
            # None of the texts should be raw i18n key names; they should resolve.
            assert text and not text.startswith("tariff_") and text != "btn_back", f"unresolved i18n in {lang}: {text}"


async def _test_birth_date_parsing() -> None:
    assert _parse_birth_date("07.03.1995").isoformat() == "1995-03-07"
    assert _parse_birth_date("7.3.1995").isoformat() == "1995-03-07"
    assert _parse_birth_date("31.02.1995") is None
    assert _parse_birth_date("not a date") is None
    assert _parse_birth_date("") is None


async def _test_i18n_key_parity() -> None:
    import json
    import pathlib

    base = pathlib.Path(__file__).parent.parent / "bot" / "i18n" / "locales"
    ru = json.loads((base / "ru.json").read_text(encoding="utf-8"))
    en = json.loads((base / "en.json").read_text(encoding="utf-8"))
    assert ru.keys() == en.keys(), f"i18n key mismatch: {set(ru) ^ set(en)}"


async def main() -> None:
    await _test_voice_fallback()
    await _test_paywall_i18n()
    await _test_birth_date_parsing()
    await _test_i18n_key_parity()
    print("PATCH 1 TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
