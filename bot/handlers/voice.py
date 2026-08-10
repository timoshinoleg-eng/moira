from __future__ import annotations

import html
import io
import logging
import time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..config import Config
from ..db.database import get_session
from ..db.models import User
from ..i18n import t
from ..keyboards import main_menu_kb, voice_consent_kb, voice_transcript_kb, voice_waiting_kb
from ..services.analytics import Analytics
from ..tarot import SPREADS
from ..voice.transcribe import DeepgramTranscriber, VoiceTranscriptionError
from .helpers import get_or_create_user
from .reading import run_reading

logger = logging.getLogger(__name__)
router = Router()


class VoiceInputStates(StatesGroup):
    waiting_consent = State()
    waiting_audio = State()
    waiting_confirmation = State()
    waiting_edit = State()


def _is_enabled(cfg: Config) -> bool:
    return bool(cfg.deepgram_stt_enabled and cfg.deepgram_api_key)


def _bucket(seconds: float) -> str:
    if seconds <= 3:
        return "le_3s"
    if seconds <= 8:
        return "le_8s"
    if seconds <= 15:
        return "le_15s"
    return "gt_15s"


async def _begin_voice_input(message: Message, state: FSMContext, lang: str, spread_id: str) -> None:
    await state.set_state(VoiceInputStates.waiting_audio)
    await state.update_data(spread_id=spread_id)
    await message.answer(t(lang, "voice_ready"), reply_markup=voice_waiting_kb(lang))


async def _show_transcript(message: Message, lang: str, transcript: str) -> None:
    await message.answer(
        t(lang, "voice_transcript", transcript=html.escape(transcript)),
        reply_markup=voice_transcript_kb(lang),
    )


async def _accept_consent(user_id: int) -> None:
    async with get_session() as session:
        user = await session.get(User, user_id)
        if user is not None:
            user.voice_transcription_consent = True
            await session.commit()


@router.callback_query(F.data.startswith("voice:start:"))
async def cb_voice_start(
    callback: CallbackQuery, state: FSMContext, cfg: Config, analytics: Analytics
) -> None:
    spread_id = callback.data.rsplit(":", 1)[-1]
    if spread_id not in SPREADS:
        await callback.answer("?")
        return
    user = await get_or_create_user(callback.from_user, cfg)
    lang = user.language
    if not _is_enabled(cfg):
        await callback.message.answer(t(lang, "voice_feature_unavailable"))
        await callback.answer()
        return
    await analytics.track(user.id, "voice_entry_opened", spread=spread_id, source="voice")
    if user.voice_transcription_consent:
        await _begin_voice_input(callback.message, state, lang, spread_id)
    else:
        await state.set_state(VoiceInputStates.waiting_consent)
        await state.update_data(spread_id=spread_id)
        await callback.message.answer(t(lang, "voice_consent_short"), reply_markup=voice_consent_kb(lang))
    await callback.answer()


@router.callback_query(F.data == "voice:consent:yes")
async def cb_voice_consent(
    callback: CallbackQuery, state: FSMContext, cfg: Config, analytics: Analytics
) -> None:
    data = await state.get_data()
    spread_id = data.get("spread_id")
    if spread_id not in SPREADS:
        await state.clear()
        await callback.answer("?")
        return
    user = await get_or_create_user(callback.from_user, cfg)
    if not _is_enabled(cfg):
        await callback.message.answer(t(user.language, "voice_feature_unavailable"))
        await callback.answer()
        return
    await _accept_consent(user.id)
    await analytics.track(user.id, "voice_consent_accepted", spread=spread_id, source="voice")
    await _begin_voice_input(callback.message, state, user.language, spread_id)
    await callback.answer()


@router.callback_query(F.data == "voice:cancel")
async def cb_voice_cancel(callback: CallbackQuery, state: FSMContext, cfg: Config) -> None:
    await state.clear()
    user = await get_or_create_user(callback.from_user, cfg)
    await callback.message.answer(t(user.language, "menu_help"), reply_markup=main_menu_kb(user.language))
    await callback.answer()


@router.callback_query(F.data == "voice:repeat")
async def cb_voice_repeat(callback: CallbackQuery, state: FSMContext, cfg: Config) -> None:
    data = await state.get_data()
    spread_id = data.get("spread_id")
    if spread_id not in SPREADS:
        await state.clear()
        await callback.answer("?")
        return
    user = await get_or_create_user(callback.from_user, cfg)
    await _begin_voice_input(callback.message, state, user.language, spread_id)
    await callback.answer()


@router.message(VoiceInputStates.waiting_audio, F.voice | F.audio)
async def process_voice(
    message: Message, state: FSMContext, cfg: Config, analytics: Analytics
) -> None:
    data = await state.get_data()
    spread_id = data.get("spread_id")
    if spread_id not in SPREADS:
        await state.clear()
        return
    user = await get_or_create_user(message.from_user, cfg)
    lang = user.language
    if not _is_enabled(cfg):
        await message.answer(t(lang, "voice_feature_unavailable"))
        return
    media = message.voice or message.audio
    if media is None:
        return
    duration = int(getattr(media, "duration", 0) or 0)
    if duration > cfg.deepgram_stt_max_duration_sec:
        await analytics.track(user.id, "voice_transcription_failed", spread=spread_id, error="audio_too_long")
        await message.answer(
            t(lang, "voice_too_long", seconds=cfg.deepgram_stt_max_duration_sec),
            reply_markup=voice_waiting_kb(lang),
        )
        return
    declared_size = int(getattr(media, "file_size", 0) or 0)
    if declared_size > cfg.deepgram_stt_max_bytes:
        await analytics.track(user.id, "voice_transcription_failed", spread=spread_id, error="audio_too_large")
        await message.answer(t(lang, "voice_too_large"), reply_markup=voice_waiting_kb(lang))
        return

    status = await message.answer(t(lang, "voice_transcribing"))
    started = time.monotonic()
    try:
        tg_file = await message.bot.get_file(media.file_id)
        if not tg_file.file_path:
            raise VoiceTranscriptionError("telegram_download")
        buffer = io.BytesIO()
        await message.bot.download_file(tg_file.file_path, destination=buffer)
        audio = buffer.getvalue()
        if len(audio) > cfg.deepgram_stt_max_bytes:
            raise VoiceTranscriptionError("audio_too_large")
        content_type = getattr(media, "mime_type", None) or ("audio/ogg" if message.voice else "audio/mpeg")
        transcript = await DeepgramTranscriber(
            cfg.deepgram_api_key or "",
            endpoint=cfg.deepgram_stt_endpoint,
            model=cfg.deepgram_stt_model,
            timeout_sec=cfg.deepgram_stt_timeout_sec,
        ).transcribe(audio, language=lang, content_type=content_type)
    except VoiceTranscriptionError as exc:
        logger.info("voice transcription did not complete category=%s", exc.category)
        await analytics.track(user.id, "voice_transcription_failed", spread=spread_id, error=exc.category)
        await status.edit_text(t(lang, "voice_transcription_failed"), reply_markup=voice_waiting_kb(lang))
        return
    except Exception:  # noqa: BLE001
        logger.warning("voice transcription failed before a transcript was produced")
        await analytics.track(user.id, "voice_transcription_failed", spread=spread_id, error="unexpected")
        await status.edit_text(t(lang, "voice_transcription_failed"), reply_markup=voice_waiting_kb(lang))
        return

    await state.set_state(VoiceInputStates.waiting_confirmation)
    await state.update_data(spread_id=spread_id, transcript=transcript.text)
    await analytics.track(
        user.id,
        "voice_transcription_completed",
        spread=spread_id,
        locale=lang,
        source="voice",
        latency_bucket=_bucket(time.monotonic() - started),
        duration_bucket=_bucket(float(duration)),
    )
    await status.edit_text(
        t(lang, "voice_transcript", transcript=html.escape(transcript.text)),
        reply_markup=voice_transcript_kb(lang),
    )


@router.message(VoiceInputStates.waiting_audio, F.text)
async def voice_to_text_fallback(message: Message, state: FSMContext, cfg: Config, analytics: Analytics) -> None:
    data = await state.get_data()
    await state.clear()
    spread_id = data.get("spread_id")
    if spread_id in SPREADS:
        await run_reading(message, spread_id, (message.text or "").strip(), cfg, analytics)


@router.message(VoiceInputStates.waiting_audio)
async def prompt_voice_or_text(message: Message, cfg: Config) -> None:
    user = await get_or_create_user(message.from_user, cfg)
    await message.answer(t(user.language, "voice_send_audio"), reply_markup=voice_waiting_kb(user.language))


@router.callback_query(F.data == "voice:edit")
async def cb_voice_edit(callback: CallbackQuery, state: FSMContext, cfg: Config) -> None:
    data = await state.get_data()
    if not data.get("transcript"):
        await state.clear()
        await callback.answer("?")
        return
    user = await get_or_create_user(callback.from_user, cfg)
    await state.set_state(VoiceInputStates.waiting_edit)
    await callback.message.answer(t(user.language, "voice_edit_prompt"))
    await callback.answer()


@router.message(VoiceInputStates.waiting_edit, F.text)
async def process_voice_edit(message: Message, state: FSMContext, cfg: Config) -> None:
    text = (message.text or "").strip()
    data = await state.get_data()
    if not text or data.get("spread_id") not in SPREADS:
        return
    await state.set_state(VoiceInputStates.waiting_confirmation)
    await state.update_data(transcript=text)
    user = await get_or_create_user(message.from_user, cfg)
    await _show_transcript(message, user.language, text)


@router.callback_query(F.data == "voice:confirm")
async def cb_voice_confirm(
    callback: CallbackQuery, state: FSMContext, cfg: Config, analytics: Analytics
) -> None:
    data = await state.get_data()
    await state.clear()
    spread_id = data.get("spread_id")
    transcript = str(data.get("transcript") or "").strip()
    if spread_id not in SPREADS or not transcript:
        await callback.answer("?")
        return
    user = await get_or_create_user(callback.from_user, cfg)
    await analytics.track(user.id, "voice_question_confirmed", spread=spread_id, source="voice")
    await callback.answer()
    await run_reading(
        callback.message,
        spread_id,
        transcript,
        cfg,
        analytics,
        input_mode="voice",
        actor=callback.from_user,
    )
