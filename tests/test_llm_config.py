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
