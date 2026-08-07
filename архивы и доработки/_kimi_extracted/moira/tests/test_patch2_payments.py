"""Patch 2 regression tests: payment idempotency, atomic consume, referral, promo, refund."""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DB_PATH", os.path.join(tempfile.gettempdir(), "moira_patch2.db"))
db_path = os.environ["DB_PATH"]
if os.path.exists(db_path):
    os.remove(db_path)

from aiogram.types import User as TgUser
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from bot.config import load_config
from bot.db.database import get_session, init_db
from bot.db.models import Payment, PromoCode, PromoRedemption, Referral, User
from bot.handlers.helpers import get_or_create_user
from bot.handlers.payment import on_payment, on_refund, process_promo
from bot.handlers.reading import _compensate_reading, _consume_reading
from bot.payments import PRODUCTS, payload_for
from bot.services.analytics import Analytics


class FakeSuccessfulPayment:
    def __init__(self, product_id: str, charge_id: str, total_amount: int, currency: str = "XTR") -> None:
        self.invoice_payload = payload_for(product_id)
        self.telegram_payment_charge_id = charge_id
        self.total_amount = total_amount
        self.currency = currency


class FakeRefundedPayment:
    def __init__(self, product_id: str, charge_id: str) -> None:
        self.invoice_payload = payload_for(product_id)
        self.telegram_payment_charge_id = charge_id


class FakeMessage:
    def __init__(self, user_id: int, payment=None, refund=None) -> None:
        self.from_user = TgUser(id=user_id, is_bot=False, first_name="Test", username=None)
        self.successful_payment = payment
        self.refunded_payment = refund
        self.sent: list[str] = []

    async def answer(self, text: str, **kwargs) -> None:
        self.sent.append(text)


def _tg_user(user_id: int, first_name: str = "Test") -> TgUser:
    return TgUser(id=user_id, is_bot=False, first_name=first_name)


def _cfg():
    return load_config(require_token=False)


class FakeAnalytics:
    async def track(self, *args, **kwargs) -> None:
        pass


async def _test_payment_grants_entitlement() -> None:
    cfg = _cfg()
    user = await get_or_create_user(_tg_user(100), cfg)
    before = user.free_readings

    msg = FakeMessage(100, payment=FakeSuccessfulPayment("reading_1", "chg_100", 25))
    await on_payment(msg, cfg, FakeAnalytics())

    async with get_session() as session:
        u = await session.get(User, 100)
        assert u.free_readings == before + 1, f"got {u.free_readings}"
        p = (await session.execute(select(Payment).where(Payment.charge_id == "chg_100"))).scalar_one()
        assert p.status == "paid"


async def _test_duplicate_payment_noop() -> None:
    cfg = _cfg()
    await get_or_create_user(_tg_user(101), cfg)
    msg = FakeMessage(101, payment=FakeSuccessfulPayment("reading_1", "chg_101", 25))
    await on_payment(msg, cfg, FakeAnalytics())
    before = msg.sent[:]
    await on_payment(msg, cfg, FakeAnalytics())
    async with get_session() as session:
        count = (await session.execute(select(func.count()).select_from(Payment).where(Payment.charge_id == "chg_101"))).scalar_one()
        assert count == 1, f"duplicate payment created, count={count}"


async def _test_parallel_payment_single_grant() -> None:
    cfg = _cfg()
    user = await get_or_create_user(_tg_user(102), cfg)
    before = user.free_readings

    async def fire():
        msg = FakeMessage(102, payment=FakeSuccessfulPayment("reading_1", "chg_102", 25))
        await on_payment(msg, cfg, FakeAnalytics())

    await asyncio.gather(fire(), fire())
    async with get_session() as session:
        count = (await session.execute(select(func.count()).select_from(Payment).where(Payment.charge_id == "chg_102"))).scalar_one()
        u = await session.get(User, 102)
        assert count == 1, f"parallel payments created {count} rows"
        assert u.free_readings == before + 1, f"balance wrong: {u.free_readings}"


async def _test_payment_rejects_bad_amount() -> None:
    cfg = _cfg()
    await get_or_create_user(_tg_user(103), cfg)
    msg = FakeMessage(103, payment=FakeSuccessfulPayment("reading_1", "chg_103", 24))
    await on_payment(msg, cfg, FakeAnalytics())
    async with get_session() as session:
        count = (await session.execute(select(func.count()).select_from(Payment).where(Payment.user_id == 103))).scalar_one()
        assert count == 0, "bad amount accepted"


async def _test_payment_rejects_unknown_payload() -> None:
    cfg = _cfg()
    await get_or_create_user(_tg_user(104), cfg)
    msg = FakeMessage(104, payment=FakeSuccessfulPayment("unknown", "chg_104", 25))
    await on_payment(msg, cfg, FakeAnalytics())
    async with get_session() as session:
        count = (await session.execute(select(func.count()).select_from(Payment).where(Payment.user_id == 104))).scalar_one()
        assert count == 0, "unknown product accepted"


async def _test_referral_once() -> None:
    cfg = _cfg()
    referrer = await get_or_create_user(_tg_user(200), cfg)
    referrer_before = referrer.free_readings
    referred = await get_or_create_user(_tg_user(201), cfg, referred_by=200)

    msg = FakeMessage(201, payment=FakeSuccessfulPayment("reading_1", "chg_201", 25))
    await on_payment(msg, cfg, FakeAnalytics())

    async with get_session() as session:
        ref = (await session.execute(select(Referral).where(Referral.referred_id == 201))).scalar_one()
        assert ref.rewarded is True
        r = await session.get(User, 200)
        assert r.free_readings == referrer_before + cfg.referral_reward

    # Second payment by referred user must not grant again.
    msg2 = FakeMessage(201, payment=FakeSuccessfulPayment("reading_1", "chg_201_2", 25))
    await on_payment(msg2, cfg, FakeAnalytics())
    async with get_session() as session:
        refs = (await session.execute(select(func.count()).select_from(Referral).where(Referral.referred_id == 201))).scalar_one()
        assert refs == 1


async def _test_self_referral_blocked() -> None:
    cfg = _cfg()
    user = await get_or_create_user(_tg_user(202), cfg, referred_by=202)
    msg = FakeMessage(202, payment=FakeSuccessfulPayment("reading_1", "chg_202", 25))
    await on_payment(msg, cfg, FakeAnalytics())
    async with get_session() as session:
        ref = (await session.execute(select(Referral).where(Referral.referred_id == 202))).scalar_one_or_none()
        assert ref is None


async def _test_refund_idempotent() -> None:
    cfg = _cfg()
    await get_or_create_user(_tg_user(300), cfg)
    pay = FakeMessage(300, payment=FakeSuccessfulPayment("reading_1", "chg_300", 25))
    await on_payment(pay, cfg, FakeAnalytics())

    async with get_session() as session:
        u = await session.get(User, 300)
        before = u.free_readings

    ref1 = FakeMessage(300, refund=FakeRefundedPayment("reading_1", "chg_300"))
    await on_refund(ref1, cfg, FakeAnalytics())
    ref2 = FakeMessage(300, refund=FakeRefundedPayment("reading_1", "chg_300"))
    await on_refund(ref2, cfg, FakeAnalytics())

    async with get_session() as session:
        u = await session.get(User, 300)
        assert u.free_readings == before - 1
        p = (await session.execute(select(Payment).where(Payment.charge_id == "chg_300"))).scalar_one()
        assert p.status == "refunded"


async def _test_atomic_consume_no_double_spend() -> None:
    cfg = _cfg()
    user = await get_or_create_user(_tg_user(400), cfg)
    # Reset to exactly one free reading.
    async with get_session() as session:
        u = await session.get(User, 400)
        u.free_readings = 1
        u.promo_readings = 0
        u.unlimited_until = None
        await session.commit()

    async def spend():
        # Refresh detached user object from DB to avoid stale ORM state.
        async with get_session() as session:
            u = await session.get(User, 400)
        return await _consume_reading(u)

    results = await asyncio.gather(spend(), spend())
    # Exactly one should succeed, the other must hit paywall.
    assert results.count("free") == 1, f"double spend: {results}"
    assert results.count(None) == 1, f"expected one None: {results}"

    async with get_session() as session:
        u = await session.get(User, 400)
        assert u.free_readings == 0, f"balance not zero: {u.free_readings}"


async def _test_compensate_returns_credit() -> None:
    cfg = _cfg()
    user = await get_or_create_user(_tg_user(401), cfg)
    async with get_session() as session:
        u = await session.get(User, 401)
        u.free_readings = 1
        u.promo_readings = 0
        await session.commit()

    reason = await _consume_reading(user)
    assert reason == "free"
    await _compensate_reading(user, reason)

    async with get_session() as session:
        u = await session.get(User, 401)
        assert u.free_readings == 1, f"compensation failed: {u.free_readings}"


async def _test_promo_redeem_once() -> None:
    cfg = _cfg()
    tg = _tg_user(500)
    await get_or_create_user(tg, cfg)
    async with get_session() as session:
        session.add(PromoCode(code="DEMO", kind="readings", amount=5))
        await session.commit()

    class FakeState:
        def __init__(self):
            self.data = {}
        async def clear(self):
            pass
        async def set_state(self, *args):
            pass

    class PromoMsg:
        def __init__(self, text):
            self.text = text
            self.from_user = tg
            self.sent = []
        async def answer(self, text, **kwargs):
            self.sent.append(text)

    msg1 = PromoMsg("DEMO")
    await process_promo(msg1, FakeState(), cfg, FakeAnalytics())
    assert any("+5" in s or "accepted" in s.lower() for s in msg1.sent), msg1.sent

    msg2 = PromoMsg("DEMO")
    await process_promo(msg2, FakeState(), cfg, FakeAnalytics())
    assert any("used" in s.lower() or "already" in s.lower() for s in msg2.sent), msg2.sent


async def main() -> None:
    cfg = _cfg()
    await init_db(db_path)
    await _test_payment_grants_entitlement()
    await _test_duplicate_payment_noop()
    await _test_parallel_payment_single_grant()
    await _test_payment_rejects_bad_amount()
    await _test_payment_rejects_unknown_payload()
    await _test_referral_once()
    await _test_self_referral_blocked()
    await _test_refund_idempotent()
    await _test_atomic_consume_no_double_spend()
    await _test_compensate_returns_credit()
    await _test_promo_redeem_once()
    print("PATCH 2 TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
