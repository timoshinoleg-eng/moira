from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bot.handlers.payment import _revoke_unlimited_days


def test_refund_of_second_stacked_week_preserves_first_week() -> None:
    now = datetime(2026, 8, 17, 8, 30, tzinfo=timezone.utc)
    stacked_until = now + timedelta(days=14)

    remaining = _revoke_unlimited_days(stacked_until, 7, now)

    assert remaining == now + timedelta(days=7)


def test_refunds_remove_only_the_refunded_duration_until_no_entitlement_remains() -> None:
    now = datetime(2026, 8, 17, 8, 30, tzinfo=timezone.utc)
    stacked_until = now + timedelta(days=37)  # 7-day product plus 30-day product

    after_30_day_refund = _revoke_unlimited_days(stacked_until, 30, now)
    after_final_7_day_refund = _revoke_unlimited_days(after_30_day_refund, 7, now)

    assert after_30_day_refund == now + timedelta(days=7)
    assert after_final_7_day_refund is None


def test_refund_never_creates_negative_or_expired_unlimited_time() -> None:
    now = datetime(2026, 8, 17, 8, 30, tzinfo=timezone.utc)

    assert _revoke_unlimited_days(now + timedelta(days=7), 30, now) is None
    assert _revoke_unlimited_days(now - timedelta(seconds=1), 7, now) is None
    assert _revoke_unlimited_days(None, 7, now) is None
