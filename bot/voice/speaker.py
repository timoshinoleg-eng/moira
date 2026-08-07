from __future__ import annotations

import io
import logging
import re

logger = logging.getLogger(__name__)

VOICES = {
    "ru": "ru-RU-SvetlanaNeural",
    "en": "en-US-AriaNeural",
}

MAX_CHARS = 1000


def clean_for_speech(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[🔮✨🃏❤️⚖️💎🌙👑🎁⚠️⭐]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_CHARS]


async def synthesize_reading_voice(text: str, lang: str = "ru") -> bytes | None:
    """Return MP3 bytes or None on failure/unavailable."""
    clean = clean_for_speech(text)
    if len(clean) < 20:
        return None
    try:
        import edge_tts

        voice = VOICES.get(lang, VOICES["en"])
        communicate = edge_tts.Communicate(clean, voice)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                buf.write(chunk["data"])
        data = buf.getvalue()
        return data if len(data) > 4000 else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("TTS failed: %s", exc)
        return None
