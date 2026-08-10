from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=True)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: tuple[int, ...]
    openrouter_api_key: str | None
    llm_model: str
    llm_base_url: str
    db_path: str
    bot_display_name: str
    free_readings: int
    earlybird_limit: int
    earlybird_bonus: int
    posthog_api_key: str | None
    posthog_host: str
    sentry_dsn: str | None
    referral_reward: int
    deepgram_api_key: str | None
    deepgram_stt_enabled: bool
    deepgram_stt_model: str
    deepgram_stt_endpoint: str
    deepgram_stt_max_duration_sec: int
    deepgram_stt_max_bytes: int
    deepgram_stt_timeout_sec: int


def load_config(require_token: bool = True) -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if require_token and not token:
        raise RuntimeError(
            "BOT_TOKEN is not set. Copy .env.example to .env and paste a token from @BotFather."
        )
    admins = tuple(
        int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x
    )
    return Config(
        bot_token=token,
        admin_ids=admins,
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip() or None,
        llm_model=os.getenv("LLM_MODEL", "deepseek/deepseek-v4-flash"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        db_path=os.getenv("DB_PATH", "moira.db"),
        bot_display_name=os.getenv("BOT_DISPLAY_NAME", "Мойра"),
        free_readings=int(os.getenv("FREE_READINGS", "3")),
        earlybird_limit=int(os.getenv("EARLYBIRD_LIMIT", "50")),
        earlybird_bonus=int(os.getenv("EARLYBIRD_BONUS", "3")),
        posthog_api_key=os.getenv("POSTHOG_API_KEY", "").strip() or None,
        posthog_host=os.getenv("POSTHOG_HOST", "https://eu.i.posthog.com"),
        sentry_dsn=os.getenv("SENTRY_DSN", "").strip() or None,
        referral_reward=int(os.getenv("REFERRAL_REWARD", "2")),
        deepgram_api_key=os.getenv("DEEPGRAM_API_KEY", "").strip() or None,
        deepgram_stt_enabled=_env_bool("DEEPGRAM_STT_ENABLED"),
        deepgram_stt_model=os.getenv("DEEPGRAM_STT_MODEL", "nova-3"),
        deepgram_stt_endpoint=os.getenv("DEEPGRAM_STT_ENDPOINT", "https://api.deepgram.com/v1/listen"),
        deepgram_stt_max_duration_sec=int(os.getenv("DEEPGRAM_STT_MAX_DURATION_SEC", "60")),
        deepgram_stt_max_bytes=int(os.getenv("DEEPGRAM_STT_MAX_BYTES", "10485760")),
        deepgram_stt_timeout_sec=int(os.getenv("DEEPGRAM_STT_TIMEOUT_SEC", "25")),
    )
