from __future__ import annotations

from scripts.check_release_secrets import scan_text


def test_secret_scanner_detects_high_confidence_credentials_without_echoing_values() -> None:
    github = "gh" + "p_" + "A" * 24
    telegram = "123456789:" + "A" * 35
    private_key = "-----BEGIN " + "PRIVATE KEY-----"

    assert scan_text(github) == ["github_token"]
    assert scan_text(telegram) == ["telegram_token"]
    assert scan_text(private_key) == ["private_key"]


def test_secret_scanner_ignores_placeholders_and_hashes() -> None:
    assert scan_text("OPENROUTER_API_KEY=your-key-here") == []
    assert scan_text("sha256=" + "a" * 64) == []
