from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.config import load_config
from bot.db.database import init_db
from bot.llm.adapter import interpret_reading
from bot.tarot.deck import build_deck
from bot.tarot.spreads import DrawnCard, SPREADS


async def main() -> None:
    cfg = load_config(require_token=False)
    if not cfg.llm_backup_model:
        raise SystemExit("LLM_BACKUP_MODEL is not configured.")

    isolated_db = Path(tempfile.gettempdir()) / "moira_backup_oracle_smoke.db"
    backup_cfg = replace(
        cfg,
        llm_model=cfg.llm_backup_model,
        llm_backup_model=None,
        db_path=str(isolated_db),
    )
    await init_db(backup_cfg.db_path)
    deck = {card.id: card for card in build_deck()}
    spread = SPREADS["situation"]
    drawn = [
        DrawnCard(
            position_id=position_id,
            position_label=labels,
            card=deck[card_id],
            reversed=reversed_,
        )
        for (position_id, labels), card_id, reversed_ in zip(
            spread["positions"],
            ("major_0", "major_1", "major_2"),
            (False, False, True),
        )
    ]
    result = await interpret_reading(
        backup_cfg,
        "en",
        spread["title"]["en"],
        "What small, practical step could help me clarify a changing work situation?",
        drawn,
        spread_id="situation",
    )
    print(
        json.dumps(
            {
                "backup_model": backup_cfg.llm_model,
                "structured_result": result is not None,
                "card_interpretation_count": len(result.card_interpretations) if result else 0,
                "share_summary_present": bool(result and result.share_summary),
                "output_language": "en",
            },
            ensure_ascii=False,
        )
    )
    if result is None or len(result.card_interpretations) != len(drawn):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
