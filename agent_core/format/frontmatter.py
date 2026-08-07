"""YAML frontmatter parser / writer / validator for OKF v0.2 markdown files."""

from __future__ import annotations

from typing import Any

import yaml

_FENCE = "---"


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split a markdown file into ``(frontmatter dict, body)``.

    Format: ``---\\n<yaml>\\n---\\n<body>``. Files without a leading
    frontmatter fence return ``({}, content)``.
    """
    if not content.startswith(_FENCE):
        return {}, content
    parts = content.split(_FENCE, 2)
    if len(parts) < 3:
        return {}, content
    raw_yaml = parts[1]
    try:
        meta = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    body = parts[2].strip("\n")
    return meta, body


def write_frontmatter(metadata: dict, body: str) -> str:
    """Assemble a markdown file from frontmatter metadata + body."""
    head = yaml.safe_dump(
        metadata, allow_unicode=True, sort_keys=False, default_flow_style=False
    ).strip()
    return f"{_FENCE}\n{head}\n{_FENCE}\n\n{body.strip()}\n"


def validate_frontmatter(metadata: dict) -> list[str]:
    """Check required OKF fields.

    Returns a list of error strings (empty list == valid).
    """
    errors: list[str] = []
    if not metadata.get("type"):
        errors.append("missing required field: type")
    return errors


def json_safe(value: Any) -> Any:
    """Recursively convert values into JSON-serialisable primitives."""
    import datetime as _dt

    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if hasattr(value, "value"):  # enums
        return value.value
    return value
