"""Offline smoke tests: DB ledger idempotency, referral parsing, card codecs, favorites, analytics."""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DB_PATH", os.path.join(tempfile.gettempdir(), "moira_smoke.db"))
db_path = os.environ["DB_PATH"]
if os.path.exists(db_path):
    os.remove(db_path)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from bot.config import load_config
from bot.db.database import get_session, init_db
from bot.db.models import Payment, Reading, Referral
from bot.handlers.helpers import parse_referral_param
from bot.services.analytics import Analytics
from bot.tarot.deck import cards_from_codes


async def main() -> None:
    cfg = load_config(require_token=False)
    await init_db(db_path)
    failures = []

    async with get_session() as session:
        session.add(Payment(user_id=1, product="reading_1", stars=25, charge_id="chg_A", status="paid"))
        await session.commit()
    try:
        async with get_session() as session:
            session.add(Payment(user_id=1, product="reading_1", stars=25, charge_id="chg_A", status="paid"))
            await session.commit()
        failures.append("duplicate charge_id accepted (idempotency broken)")
    except IntegrityError:
        pass

    cases = [
        ("ref_123", 999, 123),
        ("ref_123", 123, None),
        ("ref_abc", 1, None),
        ("", 1, None),
        (None, 1, None),
        ("ref_-5", 1, None),
    ]
    for param, own, expected in cases:
        got = parse_referral_param(param, own)
        if got != expected:
            failures.append(f"parse_referral_param({param!r},{own}) = {got}, expected {expected}")

    codes = ["major_0", "major_17R", "wands_ace"]
    pairs = cards_from_codes(codes)
    if len(pairs) != 3:
        failures.append(f"cards_from_codes parsed {len(pairs)} of 3")
    elif pairs[1][1] is not True or pairs[0][1] is not False:
        failures.append("reversed flag roundtrip broken")
    back = ",".join(f"{c.id}{'R' if r else ''}" for c, r in pairs)
    if back != ",".join(codes):
        failures.append(f"card code roundtrip: {back}")

    from bot.handlers.features import _toggle_favorite, _top_cards_of_week

    fav_state = await _toggle_favorite(1, 42)
    fav_state2 = await _toggle_favorite(1, 42)
    if fav_state is not True or fav_state2 is not False:
        failures.append("favorite toggle wrong")

    async with get_session() as session:
        session.add(Referral(referrer_id=7, referred_id=1, rewarded=True))
        await session.commit()
    try:
        async with get_session() as session:
            session.add(Referral(referrer_id=7, referred_id=1, rewarded=True))
            await session.commit()
        failures.append("duplicate referral reward accepted")
    except IntegrityError:
        pass

    fake = [
        Reading(user_id=1, spread="situation", cards_json="major_0,major_17,major_0"),
        Reading(user_id=1, spread="love", cards_json="major_0,wands_twoR"),
    ]
    top = _top_cards_of_week(fake, "ru", top_n=2)
    if not top or top[0] != "Шут":
        failures.append(f"top cards aggregation wrong: {top}")

    analytics = Analytics(cfg)
    await analytics.track(1, "smoke_test_event", foo="bar")
    from bot.db.models import Event

    async with get_session() as session:
        n = len((await session.execute(select(Event).where(Event.name == "smoke_test_event"))).scalars().all())
    if n != 1:
        failures.append(f"analytics event persisted {n} times, expected 1")
    analytics.shutdown()

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("ALL SMOKE TESTS PASSED")


asyncio.run(main())
