from __future__ import annotations

import json
import pathlib

_LOCALES: dict[str, dict[str, str]] = {}


def _load() -> None:
    base = pathlib.Path(__file__).parent / "locales"
    for f in sorted(base.glob("*.json")):
        _LOCALES[f.stem] = json.loads(f.read_text(encoding="utf-8"))


_load()


def t(lang: str, key: str, **kwargs) -> str:
    if lang not in _LOCALES:
        lang = "ru"
    text = _LOCALES[lang].get(key) or _LOCALES.get("ru", {}).get(key, key)
    return text.format(**kwargs) if kwargs else text


def detect_language(code: str | None) -> str:
    return "ru" if (code or "").lower().startswith("ru") else "en"
