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
