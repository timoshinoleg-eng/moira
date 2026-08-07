from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=True)


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
        llm_model=os.getenv("LLM_MODEL", "deepseek/deepseek-chat"),
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
    )
