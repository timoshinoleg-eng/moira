from __future__ import annotations

from urllib.parse import urlencode

_INVITE_VARIANTS = ("a", "b")


def invite_variant(user_id: int) -> str:
    """Stable A/B assignment shared by every invite opened by one user."""
    return _INVITE_VARIANTS[user_id % len(_INVITE_VARIANTS)]


def referral_deeplink(bot_username: str, user_id: int, variant: str) -> str:
    """Return a safe Telegram /start referral link with pilot attribution."""
    username = bot_username.strip().lstrip("@")
    if not username:
        raise ValueError("bot username is required")
    if user_id <= 0:
        raise ValueError("user id must be positive")
    if variant not in _INVITE_VARIANTS:
        raise ValueError("unsupported invite variant")
    return f"https://t.me/{username}?start=ref_{user_id}_{variant}"


def telegram_share_url(text: str, link: str) -> str:
    """Use Telegram's native share sheet without putting private data in the URL."""
    return "https://t.me/share/url?" + urlencode({"url": link, "text": text})
