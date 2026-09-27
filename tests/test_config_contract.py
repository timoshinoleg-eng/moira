"""Characterisation of bot.config: the exact contract the settings rewrite must keep.

These tests were written against the hand-rolled dataclass and are expected to
pass unchanged after the move to pydantic-settings. Anything that looks like a
quirk here is deliberate:

- unknown boolean strings are False, not a validation error;
- several numeric settings clamp instead of rejecting;
- DATABASE_URL stays "" while other optional secrets become None;
- ``*_FILE`` reads a secret from disk for Docker secrets.
"""
from __future__ import annotations

import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bot.config import Config, load_config  # noqa: E402

# Every variable load_config reads, so a developer's real .env cannot leak in.
ENV_NAMES = [
    "BOT_TOKEN",
    "ADMIN_IDS",
    "OPENROUTER_API_KEY",
    "LLM_API_KEY_FILE",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "LLM_BACKUP_MODEL",
    "LLM_PROMPT_VERSION",
    "LLM_JSON_MODE",
    "LLM_RETRY_POLICY_V2",
    "LLM_CONTROLLED_REPAIR_ENABLED",
    "LLM_V1_TIMEOUT_SEC",
    "LLM_V1_MAX_RETRIES",
    "LLM_V2_PRIMARY_TIMEOUT_SEC",
    "LLM_V2_TOTAL_TIMEOUT_SEC",
    "LLM_V2_MAX_ATTEMPTS",
    "DB_PATH",
    "DATABASE_URL",
    "BOT_DISPLAY_NAME",
    "FREE_READINGS",
    "EARLYBIRD_LIMIT",
    "EARLYBIRD_BONUS",
    "POSTHOG_API_KEY",
    "POSTHOG_HOST",
    "SENTRY_DSN",
    "REFERRAL_REWARD",
    "DEEPGRAM_API_KEY",
    "DEEPGRAM_STT_ENABLED",
    "DEEPGRAM_STT_MODEL",
    "DEEPGRAM_STT_ENDPOINT",
    "DEEPGRAM_STT_MAX_DURATION_SEC",
    "DEEPGRAM_STT_MAX_BYTES",
    "DEEPGRAM_STT_TIMEOUT_SEC",
    "SPREAD_ANIMATION",
    "PUSH_WORKER_ENABLED",
    "PUSH_HOUR_UTC",
    "PUSH_TICK_SECONDS",
    "PUSH_BATCH_SIZE",
    "PUSH_LEASE_SECONDS",
    "PUSH_MAX_ATTEMPTS",
    "PUSH_MIRROR_ENABLED",
]


@pytest.fixture
def clean_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


# --- the token guard ---------------------------------------------------------


def test_token_is_required_by_default(clean_env) -> None:
    with pytest.raises(RuntimeError) as exc:
        load_config()
    assert "BOT_TOKEN is not set" in str(exc.value)


def test_require_token_false_allows_an_empty_token(clean_env) -> None:
    assert load_config(require_token=False).bot_token == ""


def test_token_is_stripped(clean_env) -> None:
    clean_env.setenv("BOT_TOKEN", "  123:abc  ")
    assert load_config(require_token=False).bot_token == "123:abc"


def test_whitespace_only_token_still_fails_the_guard(clean_env) -> None:
    clean_env.setenv("BOT_TOKEN", "   ")
    with pytest.raises(RuntimeError):
        load_config()


# --- booleans stay lenient ---------------------------------------------------


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "Yes", "on", " on ", "TrUe"])
def test_truthy_spellings(clean_env, raw: str) -> None:
    clean_env.setenv("SPREAD_ANIMATION", raw)
    assert load_config(require_token=False).spread_animation is True


@pytest.mark.parametrize("raw", ["0", "false", "no", "off", "", "  ", "maybe", "2", "null"])
def test_everything_else_is_false_not_an_error(clean_env, raw: str) -> None:
    clean_env.setenv("SPREAD_ANIMATION", raw)
    assert load_config(require_token=False).spread_animation is False


def test_absent_boolean_uses_the_documented_default(clean_env) -> None:
    cfg = load_config(require_token=False)
    assert cfg.spread_animation is False
    assert cfg.push_worker_enabled is False
    assert cfg.deepgram_stt_enabled is False
    # The one boolean that ships on.
    assert cfg.push_mirror_enabled is True


def test_push_mirror_can_be_switched_off(clean_env) -> None:
    clean_env.setenv("PUSH_MIRROR_ENABLED", "no")
    assert load_config(require_token=False).push_mirror_enabled is False


def test_push_mirror_garbage_is_false_rather_than_the_true_default(clean_env) -> None:
    clean_env.setenv("PUSH_MIRROR_ENABLED", "perhaps")
    assert load_config(require_token=False).push_mirror_enabled is False


def test_an_empty_push_mirror_var_is_false_not_the_default(clean_env) -> None:
    """`PUSH_MIRROR_ENABLED=` in a compose file means "off", not "unset"."""
    clean_env.setenv("PUSH_MIRROR_ENABLED", "")
    assert load_config(require_token=False).push_mirror_enabled is False


# --- clamping, not validation ------------------------------------------------


def test_llm_v2_max_attempts_is_clamped_to_one_or_two(clean_env) -> None:
    for raw, expected in (("0", 1), ("1", 1), ("2", 2), ("5", 2), ("99", 2)):
        clean_env.setenv("LLM_V2_MAX_ATTEMPTS", raw)
        assert load_config(require_token=False).llm_v2_max_attempts == expected, raw


@pytest.mark.parametrize(
    ("name", "raw", "expected"),
    [
        ("PUSH_TICK_SECONDS", "10", 30),
        ("PUSH_TICK_SECONDS", "30", 30),
        ("PUSH_BATCH_SIZE", "0", 1),
        ("PUSH_LEASE_SECONDS", "5", 30),
        ("PUSH_MAX_ATTEMPTS", "0", 1),
    ],
)
def test_floor_clamps(clean_env, name: str, raw: str, expected: int) -> None:
    clean_env.setenv(name, raw)
    assert getattr(load_config(require_token=False), name.lower()) == expected


def test_timeouts_default_to_floats(clean_env) -> None:
    cfg = load_config(require_token=False)
    assert cfg.llm_v2_primary_timeout_sec == 12.0
    assert isinstance(cfg.llm_v2_primary_timeout_sec, float)
    clean_env.setenv("LLM_V2_PRIMARY_TIMEOUT_SEC", "9.5")
    assert load_config(require_token=False).llm_v2_primary_timeout_sec == 9.5


def test_v1_llm_timeout_is_tunable_and_defaults_to_the_historical_budget(clean_env) -> None:
    """The single-request policy had a hardcoded 90s client timeout.

    A slow-but-correct provider could not be used and a fast-but-wrong one could
    not be cut short without waiting out the full budget, so the value is read
    from the environment while keeping the previous default.
    """
    cfg = load_config(require_token=False)
    assert cfg.llm_v1_timeout_sec == 90.0
    assert isinstance(cfg.llm_v1_timeout_sec, float)
    clean_env.setenv("LLM_V1_TIMEOUT_SEC", "25")
    assert load_config(require_token=False).llm_v1_timeout_sec == 25.0


def test_v1_llm_retries_are_explicit(clean_env) -> None:
    """The SDK default of 2 retries silently multiplies the timeout budget."""
    assert load_config(require_token=False).llm_v1_max_retries == 2
    clean_env.setenv("LLM_V1_MAX_RETRIES", "0")
    assert load_config(require_token=False).llm_v1_max_retries == 0


def test_push_hour_is_not_clamped(clean_env) -> None:
    clean_env.setenv("PUSH_HOUR_UTC", "23")
    assert load_config(require_token=False).push_hour_utc == 23


# --- admin ids ---------------------------------------------------------------


def test_admin_ids_parse_comma_separated(clean_env) -> None:
    clean_env.setenv("ADMIN_IDS", "1,2, 3")
    assert load_config(require_token=False).admin_ids == (1, 2, 3)


def test_empty_admin_ids_become_an_empty_tuple(clean_env) -> None:
    for raw in ("", "   ", ",,", " , "):
        clean_env.setenv("ADMIN_IDS", raw)
        assert load_config(require_token=False).admin_ids == (), repr(raw)


# --- optional secrets --------------------------------------------------------


def test_empty_optional_secrets_become_none(clean_env) -> None:
    clean_env.setenv("POSTHOG_API_KEY", "   ")
    clean_env.setenv("SENTRY_DSN", "")
    clean_env.setenv("DEEPGRAM_API_KEY", "")
    clean_env.setenv("LLM_BACKUP_MODEL", "  ")
    cfg = load_config(require_token=False)
    assert cfg.posthog_api_key is None
    assert cfg.sentry_dsn is None
    assert cfg.deepgram_api_key is None
    assert cfg.llm_backup_model is None


def test_database_url_stays_an_empty_string(clean_env) -> None:
    """Distinct from the secrets: "" means "not configured", not "unset"."""
    assert load_config(require_token=False).database_url == ""


def test_llm_prompt_version_falls_back_when_blank(clean_env) -> None:
    clean_env.setenv("LLM_PROMPT_VERSION", "  ")
    assert load_config(require_token=False).llm_prompt_version == "v7-minor-content"


def test_secret_can_come_from_a_file(clean_env, tmp_path) -> None:
    secret = tmp_path / "openrouter.key"
    secret.write_text("sk-from-disk\n", encoding="utf-8")
    clean_env.setenv("LLM_API_KEY_FILE", str(secret))
    assert load_config(require_token=False).openrouter_api_key == "sk-from-disk"


def test_an_empty_secret_file_yields_none(clean_env, tmp_path) -> None:
    secret = tmp_path / "empty.key"
    secret.write_text("\n\n", encoding="utf-8")
    clean_env.setenv("LLM_API_KEY_FILE", str(secret))
    assert load_config(require_token=False).openrouter_api_key is None


def test_an_unreadable_secret_file_is_a_clear_error(clean_env, tmp_path) -> None:
    clean_env.setenv("LLM_API_KEY_FILE", str(tmp_path / "nope.key"))
    with pytest.raises(RuntimeError) as exc:
        load_config(require_token=False)
    assert "LLM_API_KEY_FILE cannot be read" in str(exc.value)


def test_the_direct_variable_wins_over_the_file(clean_env, tmp_path) -> None:
    secret = tmp_path / "openrouter.key"
    secret.write_text("sk-from-disk", encoding="utf-8")
    clean_env.setenv("LLM_API_KEY_FILE", str(secret))
    clean_env.setenv("OPENROUTER_API_KEY", "sk-from-env")
    assert load_config(require_token=False).openrouter_api_key == "sk-from-env"


# --- the rest of the defaults ------------------------------------------------


def test_documented_defaults(clean_env) -> None:
    cfg = load_config(require_token=False)
    assert cfg.llm_model == "deepseek/deepseek-v4-flash"
    assert cfg.llm_base_url == "https://openrouter.ai/api/v1"
    assert cfg.db_path == "moira.db"
    assert cfg.bot_display_name == "Мойра"
    assert cfg.free_readings == 3
    assert cfg.earlybird_limit == 50
    assert cfg.earlybird_bonus == 3
    assert cfg.posthog_host == "https://eu.i.posthog.com"
    assert cfg.referral_reward == 2
    assert cfg.deepgram_stt_model == "nova-3"
    assert cfg.deepgram_stt_endpoint == "https://api.deepgram.com/v1/listen"
    assert cfg.deepgram_stt_max_duration_sec == 60
    assert cfg.deepgram_stt_max_bytes == 10485760
    assert cfg.deepgram_stt_timeout_sec == 25
    assert cfg.push_hour_utc == 6
    assert cfg.push_tick_seconds == 300
    assert cfg.push_batch_size == 50
    assert cfg.push_lease_seconds == 300
    assert cfg.push_max_attempts == 3
    assert cfg.llm_json_mode is False
    assert cfg.llm_retry_policy_v2 is False
    assert cfg.llm_controlled_repair_enabled is False


def test_every_setting_is_covered_by_this_file() -> None:
    """A new field on Config must get a test here, so ENV_NAMES has to track it.

    pydantic-settings derives the variable name from the field, so the variables
    this suite isolates are the upper-cased field names plus the side channels
    that a model validator reads by hand.
    """
    side_channels = {"LLM_API_KEY_FILE"}
    derived = {name.upper() for name in Config.model_fields} | side_channels
    assert derived == set(ENV_NAMES), (
        "ENV_NAMES is out of sync with Config; "
        f"missing={sorted(derived - set(ENV_NAMES))} extra={sorted(set(ENV_NAMES) - derived)}"
    )


def test_env_lookup_is_case_insensitive() -> None:
    """Guards a bug that only shows up off Windows.

    With `case_sensitive=True`, pydantic-settings looks up the field name
    verbatim (`bot_token`) and matches the environment exactly, so the
    documented `BOT_TOKEN` is never found. A Windows dev box hides this,
    because os.environ folds case there; the Linux container does not. Asserting
    the flag directly is the only check that discriminates on both.
    """
    assert Config.model_config.get("case_sensitive", False) is False


def test_an_uppercase_env_var_is_found_on_any_platform(clean_env) -> None:
    """The spelling every deployment actually uses."""
    clean_env.setenv("BOT_TOKEN", "upper-case-token")
    assert load_config(require_token=False).bot_token == "upper-case-token"


def test_the_environment_is_read_in_exactly_one_place() -> None:
    """A stray os.getenv in a field default would bypass the isolation above.

    `_read_secret_file` is the single legitimate reader: the `LLM_API_KEY_FILE`
    side channel is not a field, so it cannot come from the settings layer.
    """
    import bot.config as cfgmod

    source = pathlib.Path(cfgmod.__file__).read_text(encoding="utf-8")
    assert source.count("os.getenv(") == 1, (
        "only _read_secret_file may touch the environment directly"
    )
    # Subscript and .get() forms are code, so prose about the environment mapping
    # does not trip these.
    assert "os.environ[" not in source
    assert "os.environ.get(" not in source


def test_config_is_immutable() -> None:
    """Code treats cfg as read-only; the settings object must keep that promise."""
    cfg = load_config(require_token=False)
    with pytest.raises(Exception):
        cfg.bot_token = "tampered"  # type: ignore[misc]


def test_partial_construction_still_works() -> None:
    """Several suites build a Config by hand with only the core fields."""
    cfg = Config(
        bot_token="t",
        admin_ids=(),
        openrouter_api_key=None,
        llm_model="m",
        llm_base_url="u",
        db_path="d",
        bot_display_name="n",
        free_readings=1,
        earlybird_limit=2,
        earlybird_bonus=3,
        posthog_api_key=None,
        posthog_host="h",
        sentry_dsn=None,
        referral_reward=1,
        deepgram_api_key=None,
        deepgram_stt_enabled=False,
        deepgram_stt_model="nova-3",
        deepgram_stt_endpoint="e",
        deepgram_stt_max_duration_sec=60,
        deepgram_stt_max_bytes=1,
        deepgram_stt_timeout_sec=25,
    )
    assert cfg.bot_token == "t"
    assert cfg.free_readings == 1
    assert cfg.spread_animation is False
