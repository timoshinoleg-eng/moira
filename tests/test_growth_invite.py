from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from bot.handlers.growth import invite_variant, referral_deeplink, telegram_share_url


def test_invite_variant_is_stable_and_balanced() -> None:
    assert invite_variant(1) == "b"
    assert invite_variant(2) == "a"
    assert invite_variant(1) == invite_variant(1)


def test_referral_deeplink_preserves_attribution() -> None:
    assert referral_deeplink("@MoiraOracleBot", 123, "a") == "https://t.me/MoiraOracleBot?start=ref_123_a"


def test_referral_deeplink_rejects_invalid_values() -> None:
    import pytest

    with pytest.raises(ValueError):
        referral_deeplink("", 123, "a")
    with pytest.raises(ValueError):
        referral_deeplink("MoiraOracleBot", 0, "a")
    with pytest.raises(ValueError):
        referral_deeplink("MoiraOracleBot", 123, "z")


def test_native_share_url_contains_only_share_copy_and_deeplink() -> None:
    link = referral_deeplink("MoiraOracleBot", 123, "b")
    url = telegram_share_url("A private Tarot reflection from Moira.", link)
    parsed = parse_qs(urlparse(url).query)
    assert parsed["url"] == [link]
    assert parsed["text"] == ["A private Tarot reflection from Moira."]
