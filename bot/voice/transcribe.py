from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import httpx


DEFAULT_ENDPOINT: Final = "https://api.deepgram.com/v1/listen"


class VoiceTranscriptionError(RuntimeError):
    """A user-safe Deepgram failure with an analytics-safe category."""

    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


@dataclass(frozen=True)
class VoiceTranscript:
    text: str
    confidence: float | None
    duration_sec: float | None


def _as_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_transcription(payload: dict) -> VoiceTranscript:
    """Extract one editable transcript without retaining the provider payload."""
    try:
        alternative = payload["results"]["channels"][0]["alternatives"][0]
        text = str(alternative.get("transcript") or "").strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise VoiceTranscriptionError("invalid_response") from exc
    if not text:
        raise VoiceTranscriptionError("empty_transcript")
    metadata = payload.get("metadata") or {}
    return VoiceTranscript(
        text=text,
        confidence=_as_float(alternative.get("confidence")),
        duration_sec=_as_float(metadata.get("duration")),
    )


def status_category(status_code: int) -> str:
    if status_code in {401, 403}:
        return "provider_auth"
    if status_code == 402:
        return "provider_quota"
    if status_code == 413:
        return "audio_too_large"
    if status_code == 429:
        return "provider_busy"
    return "provider_error"


class DeepgramTranscriber:
    """Small REST client for a completed Telegram voice/audio file."""

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = "nova-3",
        timeout_sec: int = 25,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint
        self._model = model
        self._timeout_sec = timeout_sec
        self._transport = transport

    async def transcribe(
        self,
        audio: bytes,
        *,
        language: str,
        content_type: str,
    ) -> VoiceTranscript:
        if not audio:
            raise VoiceTranscriptionError("empty_audio")
        headers = {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": content_type or "audio/ogg",
        }
        params = {
            "model": self._model,
            "language": language,
            "smart_format": "true",
        }
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout_sec),
                transport=self._transport,
                follow_redirects=False,
            ) as client:
                response = await client.post(
                    self._endpoint,
                    params=params,
                    headers=headers,
                    content=audio,
                )
        except httpx.TimeoutException as exc:
            raise VoiceTranscriptionError("provider_timeout") from exc
        except httpx.RequestError as exc:
            raise VoiceTranscriptionError("provider_network") from exc
        if response.is_error:
            raise VoiceTranscriptionError(status_category(response.status_code))
        try:
            return parse_transcription(response.json())
        except ValueError as exc:
            raise VoiceTranscriptionError("invalid_response") from exc
