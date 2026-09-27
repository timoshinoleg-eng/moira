from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from pydantic import BeforeValidator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# .env wins over the real environment, as it always has: an operator editing
# .env locally expects it to take effect. We deliberately do *not* also hand
# pydantic-settings an `env_file`, because that would read the same file a second
# time through a source with different precedence, and `os.environ` is already
# the single, well-defined input.
load_dotenv(override=True)

_TRUTHY = {"1", "true", "yes", "on"}


def _lenient_bool(raw: Any) -> Any:
    """Accept the usual spellings and treat everything else as False.

    A mistyped `SPREAD_ANIMATION=treu` used to mean "off" and now has to keep
    meaning that. pydantic's own bool parsing raises on unknown strings, which
    would turn a typo in a compose file into a crash loop at startup — strictly
    worse than silently keeping a feature disabled.
    """
    if raw is None or isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in _TRUTHY


def _floor(limit: int):
    def clamp(raw: Any) -> Any:
        return max(limit, int(raw))

    return clamp


def _clamp(low: int, high: int):
    def clamp(raw: Any) -> Any:
        return max(low, min(high, int(raw)))

    return clamp


def _admin_ids(raw: Any) -> tuple[int, ...]:
    """`ADMIN_IDS=1,2, 3` — a plain comma list, not the JSON a tuple field implies."""
    if isinstance(raw, (tuple, list)):
        return tuple(int(x) for x in raw)
    return tuple(int(x) for x in str(raw).replace(" ", "").split(",") if x)


def _strip(raw: Any) -> Any:
    return str(raw).strip() if raw is not None else raw


def _blank_to_none(raw: Any) -> Any:
    """An optional secret that is present but blank means "not configured"."""
    if raw is None:
        return None
    return str(raw).strip() or None


def _prompt_version(raw: Any) -> Any:
    return str(raw).strip() or "v7-minor-content"


def _read_secret_file(env_name: str) -> str | None:
    """Docker secrets: the value may live in a file instead of the environment."""
    path = os.getenv(env_name, "").strip()
    if not path:
        return None
    try:
        return Path(path).expanduser().read_text(encoding="utf-8").strip() or None
    except OSError as exc:
        # Raised as RuntimeError on purpose: pydantic wraps ValueError into a
        # ValidationError, and callers (and the operator reading the log) expect
        # to see this message as-is.
        raise RuntimeError(f"{env_name} cannot be read") from exc


LenientBool = Annotated[bool, BeforeValidator(_lenient_bool)]
AdminIds = Annotated[tuple[int, ...], NoDecode, BeforeValidator(_admin_ids)]
Stripped = Annotated[str, BeforeValidator(_strip)]
OptionalSecret = Annotated[str | None, BeforeValidator(_blank_to_none)]


class Config(BaseSettings):
    """Every setting the bot reads, in one typed place.

    Field defaults are the documented defaults, which means a test can build a
    Config by hand from just the core fields. Note that a hand-built Config still
    picks up unspecified fields from the environment, exactly as `Config()` does.
    """

    model_config = SettingsConfigDict(
        frozen=True,
        extra="ignore",
        case_sensitive=True,
        validate_default=True,
    )

    bot_token: Stripped = ""
    admin_ids: AdminIds = ()
    openrouter_api_key: OptionalSecret = None
    llm_model: str = "deepseek/deepseek-v4-flash"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    db_path: str = "moira.db"
    bot_display_name: str = "Мойра"
    free_readings: int = 3
    earlybird_limit: int = 50
    earlybird_bonus: int = 3
    posthog_api_key: OptionalSecret = None
    posthog_host: str = "https://eu.i.posthog.com"
    sentry_dsn: OptionalSecret = None
    referral_reward: int = 2
    deepgram_api_key: OptionalSecret = None
    deepgram_stt_enabled: LenientBool = False
    deepgram_stt_model: str = "nova-3"
    deepgram_stt_endpoint: str = "https://api.deepgram.com/v1/listen"
    deepgram_stt_max_duration_sec: int = 60
    deepgram_stt_max_bytes: int = 10485760
    deepgram_stt_timeout_sec: int = 25
    llm_backup_model: OptionalSecret = None
    llm_prompt_version: Annotated[str, BeforeValidator(_prompt_version)] = "v7-minor-content"
    llm_json_mode: LenientBool = False
    llm_retry_policy_v2: LenientBool = False
    llm_controlled_repair_enabled: LenientBool = False
    llm_v2_primary_timeout_sec: float = 12.0
    llm_v2_total_timeout_sec: float = 18.0
    llm_v2_max_attempts: Annotated[int, BeforeValidator(_clamp(1, 2))] = 2
    database_url: Stripped = ""
    # Off by default: the reveal clip is ~1.6 MB against ~450 KB for the still photo, so
    # enabling it by default would multiply every reading's payload before anyone
    # has measured whether it buys retention. Flip it on for a beta cohort.
    spread_animation: LenientBool = False
    # M-09 delivery worker. Off keeps the pre-ledger 20-minute loop, which stays in
    # the tree as the rollback path until the worker has proven itself in beta.
    push_worker_enabled: LenientBool = False
    push_hour_utc: int = 6
    push_tick_seconds: Annotated[int, BeforeValidator(_floor(30))] = 300
    push_batch_size: Annotated[int, BeforeValidator(_floor(1))] = 50
    push_lease_seconds: Annotated[int, BeforeValidator(_floor(30))] = 300
    push_max_attempts: Annotated[int, BeforeValidator(_floor(1))] = 3
    push_mirror_enabled: LenientBool = True

    @model_validator(mode="after")
    def _apply_secret_files(self) -> Config:
        """Fill the LLM key from `LLM_API_KEY_FILE` when the variable is empty.

        The direct variable always wins, so an operator can override a mounted
        secret without unmounting it.
        """
        if not self.openrouter_api_key:
            from_file = _read_secret_file("LLM_API_KEY_FILE")
            if from_file is not None:
                # frozen=True blocks normal assignment even inside a validator.
                object.__setattr__(self, "openrouter_api_key", from_file)
        return self


def load_config(require_token: bool = True) -> Config:
    cfg = Config()
    if require_token and not cfg.bot_token:
        raise RuntimeError(
            "BOT_TOKEN is not set. Copy .env.example to .env and paste a token from @BotFather."
        )
    return cfg
