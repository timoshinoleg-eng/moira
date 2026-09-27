"""Turn the TTS MP3 into a real Telegram voice note.

Telegram only accepts OGG/OPUS for :meth:`Message.answer_voice`. ``edge-tts``
speaks MP3, so every reading was reaching users as a plain audio attachment with
a music-player icon instead of a voice message with a waveform — the artefact the
product's "oracle speaks" moment depends on.

``imageio-ffmpeg`` is used only for its bundled ffmpeg binary, so nothing here
depends on imageio itself. The conversion is strictly best-effort: if ffmpeg is
missing, times out, or produces nothing usable, this returns ``None`` and the
caller sends the original MP3, which is exactly what shipped before.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)

# Voice notes are spoken summaries, not music: 32 kbit/s mono Opus is plenty and
# keeps a one-minute reading well under a megabyte.
OPUS_BITRATE = "32k"
OPUS_SAMPLE_RATE = "48000"
OPUS_CHANNELS = "1"
CONVERT_TIMEOUT_SEC = 30
# A converted note is never worth retrying if it comes back implausibly small.
MIN_PLAUSIBLE_BYTES = 1024

VOICE_FILENAME = "moira_voice.ogg"


def ffmpeg_exe() -> str | None:
    """Locate an ffmpeg binary: the bundled one first, then the system PATH."""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001 - the binary is an optional extra
        logger.debug("bundled ffmpeg unavailable: %s", exc)
        return shutil.which("ffmpeg")


def _convert_sync(exe: str, mp3: bytes) -> bytes | None:
    command = [
        exe,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-vn",
        # The codec must be named. Left to itself, ffmpeg picks Vorbis for the Ogg
        # container, and Telegram rejects a Vorbis stream for a voice message —
        # the request fails with a codec error rather than anything obvious.
        "-c:a",
        "libopus",
        "-ac",
        OPUS_CHANNELS,
        "-ar",
        OPUS_SAMPLE_RATE,
        "-b:a",
        OPUS_BITRATE,
        "-f",
        "ogg",
        "pipe:1",
    ]
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            command,
            input=mp3,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=CONVERT_TIMEOUT_SEC,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("ffmpeg conversion failed: %s", exc)
        return None
    if completed.returncode != 0:
        logger.warning(
            "ffmpeg exited %s: %s",
            completed.returncode,
            completed.stderr.decode("utf-8", "replace")[:200],
        )
        return None
    if len(completed.stdout) < MIN_PLAUSIBLE_BYTES:
        logger.warning("ffmpeg produced only %d bytes; keeping the mp3", len(completed.stdout))
        return None
    if not completed.stdout.startswith(b"OggS"):
        logger.warning("ffmpeg output is not an Ogg stream; keeping the mp3")
        return None
    return completed.stdout


async def to_voice_note(mp3: bytes) -> bytes | None:
    """Return OGG/OPUS bytes for a voice note, or None to keep the MP3."""
    if not mp3:
        return None
    exe = ffmpeg_exe()
    if not exe:
        logger.info("no ffmpeg available; voice notes will be sent as audio")
        return None
    return await asyncio.to_thread(_convert_sync, exe, mp3)
