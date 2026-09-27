"""Beta metrics: feedback rate, conversion funnel and d7 retention on a seeded DB."""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.db.database import close_db, get_session, init_db
from bot.db.models import Event, LlmUsage, Reading, ReadingFeedback, User
from scripts.beta_metrics import collect


def test_beta_metrics_end_to_end(tmp_path) -> None:
    async def run() -> None:
        await init_db(str(tmp_path / "moira-metrics.db"))
        now = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
        async with get_session() as session:
            session.add(User(id=1, language="ru"))
            session.add(User(id=2, language="ru"))
            # User 1: two readings 8 days apart -> d7 return; positive feedback.
            session.add(Reading(id=1, user_id=1, spread="love", cards_json="major_0",
                                generation_id="g1", created_at=now))
            session.add(Reading(id=2, user_id=1, spread="love", cards_json="major_1",
                                generation_id="g2", created_at=now + timedelta(days=8)))
            # User 2: one reading, negative feedback, no return.
            session.add(Reading(id=3, user_id=2, spread="situation", cards_json="major_2",
                                generation_id="g3", created_at=now))
            session.add(LlmUsage(user_id=1, model="m-a", provider="p", prompt_version="v7", generation_id="g1"))
            session.add(LlmUsage(user_id=1, model="m-a", provider="p", prompt_version="v7", generation_id="g2"))
            session.add(LlmUsage(user_id=2, model="m-b", provider="p", prompt_version="v6", generation_id="g3"))
            session.add(ReadingFeedback(user_id=1, reading_id=1, generation_id="g1",
                                        value="positive", checkpoint="immediate"))
            session.add(ReadingFeedback(user_id=2, reading_id=3, generation_id="g3",
                                        value="negative", checkpoint="immediate"))
            session.add(Event(name="spread_started", distinct_id="u1", props_json="{}"))
            session.add(Event(name="spread_started", distinct_id="u2", props_json="{}"))
            session.add(Event(name="spread_completed", distinct_id="u1", props_json="{}"))
            await session.commit()

        async with get_session() as session:
            report = await collect(session)

        assert report["feedback"] == {"positive": 1, "negative": 1, "positive_rate": 0.5}
        assert report["feedback_by_model"]["m-a"]["positive_rate"] == 1.0
        assert report["feedback_by_model"]["m-b"]["positive_rate"] == 0.0
        assert report["feedback_by_prompt_version"]["v7"]["positive_rate"] == 1.0
        assert report["feedback_by_spread"]["love"]["positive_rate"] == 1.0
        assert report["funnel"]["spread_started_users"] == 2
        assert report["funnel"]["spread_completed_users"] == 1
        assert report["funnel"]["conversion"] == 0.5
        assert report["retention"]["active_users"] == 2
        assert report["retention"]["d7_return_users"] == 1
        assert report["retention"]["d7_return_rate"] == 0.5
        await close_db()

    asyncio.run(run())
