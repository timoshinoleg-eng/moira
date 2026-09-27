"""Telegram voice notes need OGG/OPUS; edge-tts only speaks MP3.

The bug this guards against is quiet: ffmpeg will happily put Vorbis into an Ogg
container, the upload then fails with a codec error, and the send falls back to
an audio attachment. The user sees a music file where they expected the oracle
speaking, and nothing in the logs says why. So the assertions here are about the
*actual bytes* produced, not about the command line that produced them.
"""
from __future__ import annotations

import asyncio
import subprocess

import pytest

from bot.voice import transcode
from bot.voice.transcode import (
    MIN_PLAUSIBLE_BYTES,
    ffmpeg_exe,
    to_voice_note,
)

HAS_FFMPEG = ffmpeg_exe() is not None
needs_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="no ffmpeg available")


def _mp3_bytes(seconds: float = 2.0) -> bytes:
    """A real MP3 produced by the same ffmpeg the transcode path would use."""
    exe = ffmpeg_exe()
    assert exe, "ffmpeg required"
    completed = subprocess.run(
        [
            exe, "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"sine=frequency=320:duration={seconds}",
            "-ac", "1", "-ar", "44100", "-b:a", "64k", "-f", "mp3", "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return completed.stdout


def _stream_codec(data: bytes, tmp_path) -> str:
    """Ask ffmpeg what codec the produced stream actually is."""
    exe = ffmpeg_exe()
    assert exe
    path = tmp_path / "probe.ogg"
    path.write_bytes(data)
    probe = subprocess.run(
        [exe, "-hide_banner", "-i", str(path)], capture_output=True, check=False
    ).stderr.decode("utf-8", "replace")
    for line in probe.splitlines():
        if "Audio:" in line:
            return line
    return ""


# ------------------------------------------------------------------ content --


def test_empty_audio_is_rejected() -> None:
    assert asyncio.run(to_voice_note(b"")) is None


def test_missing_ffmpeg_degrades_to_the_mp3(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transcode, "ffmpeg_exe", lambda: None)
    assert asyncio.run(to_voice_note(b"ID3notreallyaudio")) is None


def test_garbage_input_degrades_to_the_mp3() -> None:
    assert asyncio.run(to_voice_note(b"this is not audio at all")) is None


def test_undersized_output_is_rejected() -> None:
    """A near-empty stream is a broken conversion, not a very short note."""
    assert asyncio.run(to_voice_note(b"x" * MIN_PLAUSIBLE_BYTES)) is None


@needs_ffmpeg
def test_conversion_produces_a_real_ogg_opus_stream(tmp_path) -> None:
    converted = asyncio.run(to_voice_note(_mp3_bytes()))
    assert converted is not None
    assert converted.startswith(b"OggS"), "not an Ogg stream"
    assert b"OpusHead" in converted[:64], "no Opus identification header"
    # The decisive check: the codec Telegram will inspect must actually be opus,
    # not vorbis in an Ogg wrapper.
    assert "Audio: opus" in _stream_codec(converted, tmp_path)


@needs_ffmpeg
def test_conversion_shrinks_the_payload() -> None:
    mp3 = _mp3_bytes(3.0)
    converted = asyncio.run(to_voice_note(mp3))
    assert converted is not None
    assert len(converted) < len(mp3), "voice notes should be cheaper than the mp3"


@needs_ffmpeg
def test_output_stays_opus_for_a_longer_clip(tmp_path) -> None:
    """Bitrate settings must not silently fall back on a longer input."""
    converted = asyncio.run(to_voice_note(_mp3_bytes(6.0)))
    assert converted is not None
    assert "Audio: opus" in _stream_codec(converted, tmp_path)


# ------------------------------------------------------------------ sending --


class _Recorder:
    """Captures which send method the handler reached and with what filename."""

    def __init__(self, *, voice_fails: bool = False, audio_fails: bool = False) -> None:
        self.voice_fails = voice_fails
        self.audio_fails = audio_fails
        self.calls: list[tuple[str, str]] = []
        from aiogram.types import User as TgUser

        self.from_user = TgUser(id=1, is_bot=False, first_name="T")

    async def answer_voice(self, voice, **kwargs) -> None:
        self.calls.append(("voice", voice.filename))
        if self.voice_fails:
            from aiogram.exceptions import TelegramBadRequest

            raise TelegramBadRequest(
                method=None, message="Bad Request: VOICE_MESSAGES_FORBIDDEN"
            )

    async def answer_audio(self, audio, **kwargs) -> None:
        self.calls.append(("audio", audio.filename))
        if self.audio_fails:
            raise RuntimeError("audio failed too")

    async def answer(self, text: str, **kwargs) -> None:
        self.calls.append(("text", text))


def _send(message, audio: bytes = b"ID3fake") -> str:
    from bot.handlers.reading import _send_voice_or_audio

    return asyncio.run(_send_voice_or_audio(message, audio, "ru"))


def test_converted_audio_is_sent_as_an_opus_voice(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(audio: bytes) -> bytes:
        return b"OggS" + b"\x00" * 2000

    monkeypatch.setattr("bot.handlers.reading.to_voice_note", fake)
    message = _Recorder()
    assert _send(message) == "voice_ogg"
    assert message.calls == [("voice", "moira_voice.ogg")]


def test_unconverted_audio_falls_through_to_the_mp3(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(audio: bytes) -> None:
        return None

    monkeypatch.setattr("bot.handlers.reading.to_voice_note", fake)
    message = _Recorder()
    assert _send(message) == "audio_mp3"
    assert message.calls == [("audio", "moira_voice.mp3")]


def test_a_rejected_voice_message_falls_back_to_audio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Some users have voice messages disabled; they must still hear the reading."""

    async def fake(audio: bytes) -> bytes:
        return b"OggS" + b"\x00" * 2000

    monkeypatch.setattr("bot.handlers.reading.to_voice_note", fake)
    message = _Recorder(voice_fails=True)
    assert _send(message) == "audio_mp3"
    assert [name for name, _ in message.calls] == ["voice", "audio"]


def test_a_total_failure_degrades_to_a_localised_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake(audio: bytes) -> None:
        return None

    monkeypatch.setattr("bot.handlers.reading.to_voice_note", fake)
    message = _Recorder(audio_fails=True)
    assert _send(message) == "none"
    assert message.calls[-1][0] == "text"


def test_the_sender_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    async def exploding(audio: bytes) -> bytes:
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr("bot.handlers.reading.to_voice_note", exploding)
    message = _Recorder()
    # A converter that blows up must not take the reading down with it.
    assert _send(message) == "audio_mp3"
