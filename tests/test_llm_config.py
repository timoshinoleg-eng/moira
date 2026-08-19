"""Regression coverage for the production LLM default."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import load_config


def test_default_llm_model_is_current_deepseek_flash(monkeypatch) -> None:
    monkeypatch.delenv("LLM_MODEL", raising=False)

    cfg = load_config(require_token=False)

    assert cfg.llm_model == "deepseek/deepseek-v4-flash"


def test_environment_key_overrides_legacy_key_file(monkeypatch, tmp_path) -> None:
    key_file = tmp_path / "llm-key.txt"
    key_file.write_text("file-key\n", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "environment-key")
    monkeypatch.setenv("LLM_API_KEY_FILE", str(key_file))

    cfg = load_config(require_token=False)

    assert cfg.openrouter_api_key == "environment-key"


def test_legacy_key_file_is_used_when_environment_key_is_absent(monkeypatch, tmp_path) -> None:
    key_file = tmp_path / "llm-key.txt"
    key_file.write_text("file-key\n", encoding="utf-8")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY_FILE", str(key_file))

    cfg = load_config(require_token=False)

    assert cfg.openrouter_api_key == "file-key"


def test_v2_retry_policy_is_opt_in_with_bounded_defaults(monkeypatch) -> None:
    for name in (
        "LLM_RETRY_POLICY_V2",
        "LLM_V2_PRIMARY_TIMEOUT_SEC",
        "LLM_V2_TOTAL_TIMEOUT_SEC",
        "LLM_V2_MAX_ATTEMPTS",
    ):
        monkeypatch.delenv(name, raising=False)

    cfg = load_config(require_token=False)

    assert cfg.llm_retry_policy_v2 is False
    assert cfg.llm_v2_primary_timeout_sec == 12.0
    assert cfg.llm_v2_total_timeout_sec == 18.0
    assert cfg.llm_v2_max_attempts == 2


def test_v2_retry_policy_reads_feature_flag_and_caps_attempts(monkeypatch) -> None:
    monkeypatch.setenv("LLM_RETRY_POLICY_V2", "true")
    monkeypatch.setenv("LLM_V2_PRIMARY_TIMEOUT_SEC", "9")
    monkeypatch.setenv("LLM_V2_TOTAL_TIMEOUT_SEC", "15")
    monkeypatch.setenv("LLM_V2_MAX_ATTEMPTS", "9")

    cfg = load_config(require_token=False)

    assert cfg.llm_retry_policy_v2 is True
    assert cfg.llm_v2_primary_timeout_sec == 9.0
    assert cfg.llm_v2_total_timeout_sec == 15.0
    assert cfg.llm_v2_max_attempts == 2


def test_controlled_repair_is_explicitly_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("LLM_CONTROLLED_REPAIR_ENABLED", raising=False)
    assert load_config(require_token=False).llm_controlled_repair_enabled is False

    monkeypatch.setenv("LLM_CONTROLLED_REPAIR_ENABLED", "true")
    assert load_config(require_token=False).llm_controlled_repair_enabled is True
