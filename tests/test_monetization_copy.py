from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _locale(lang: str) -> dict[str, str]:
    return json.loads((ROOT / "bot" / "i18n" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))


def test_paywall_copy_is_value_led_and_price_claim_is_not_recurring() -> None:
    ru = _locale("ru")
    en = _locale("en")
    assert "дневник" in ru["paywall_text"].lower()
    assert "diary" in en["paywall_text"].lower()
    assert "subscription" not in ru["tariff_month"].lower()
    assert "subscription" not in en["tariff_month"].lower()
