from __future__ import annotations

import hashlib
import json
import logging

from ..config import Config
from ..db.database import get_session
from ..db.models import Event

logger = logging.getLogger(__name__)


class Analytics:
    """Non-blocking product analytics.

    Events are always mirrored into the local `events` table; when POSTHOG_API_KEY
    is configured they are also shipped to PostHog Cloud (SDK never blocks handlers).
    Never pass question text, interpretations, names, usernames or birth dates as properties.
    """

    # Allowed property names. Everything else is dropped before PostHog.
    _ALLOWED_PROPS = {
        "app",
        "locale",
        "spread_type",
        "payment_product",
        "prompt_version",
        "fallback_used",
        "latency_bucket",
        "is_returning_user",
        "source",
        "spread",
        "product",
        "stars",
        "first_payment",
        "reward",
        "kind",
        "amount",
        "ai",
        "readings",
        "error",
        "error_category",
        "provider",
        "model",
        "attempts",
        "retry_policy",
        "repair_used",
        "timeout_stage",
        "reason",
        "reading_id",
        "feedback",
        "mode",
        "followup_kind",
        "duration_bucket",
        "caption_variant",
    }

    def __init__(self, cfg: Config) -> None:
        self._client = None
        self.cfg = cfg
        if cfg.posthog_api_key:
            try:
                from posthog import Posthog

                self._client = Posthog(
                    cfg.posthog_api_key,
                    host=cfg.posthog_host,
                    flush_interval=2,
                    on_error=lambda e, batch: logger.warning("posthog error: %s", e),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("PostHog init failed: %s", exc)

    @staticmethod
    def distinct(user_id: int) -> str:
        return hashlib.sha256(f"moira:{user_id}".encode()).hexdigest()[:16]

    def _safe_props(self, props: dict) -> dict:
        return {k: v for k, v in props.items() if k in self._ALLOWED_PROPS}

    async def track(self, user_id: int, event: str, **props) -> None:
        safe_props = self._safe_props(props)
        try:
            async with get_session() as session:
                session.add(
                    Event(
                        name=event,
                        distinct_id=self.distinct(user_id),
                        props_json=json.dumps(safe_props, ensure_ascii=False, default=str),
                    )
                )
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("event persist failed (%s): %s", event, exc)
        if self._client is not None:
            try:
                self._client.capture(
                    distinct_id=self.distinct(user_id),
                    event=event,
                    properties={**safe_props, "app": "moira"},
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("posthog capture failed (%s): %s", event, exc)

    def shutdown(self) -> None:
        if self._client is not None:
            try:
                self._client.flush()
                self._client.shutdown()
            except Exception:  # noqa: BLE001
                pass
