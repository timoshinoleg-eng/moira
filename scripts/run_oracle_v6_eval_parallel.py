from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from bot.config import load_config
from bot.db.database import init_db
from bot.llm.adapter import PROMPT_VERSION
from bot.tarot.deck import build_deck
from run_oracle_v6_eval import FIXTURE_PATH, make_reading, score_result

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_OUTPUT = ROOT / "docs" / "QUALITY_EVAL_V6_FULL_RESULTS.json"
PRIVATE_OUTPUT = ROOT / "docs" / "QUALITY_EVAL_V6_FULL_OWNER_REVIEW_PRIVATE.json"


async def main() -> None:
    cfg = load_config(require_token=False)
    await init_db(cfg.db_path)
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    requested_ids = {item for item in os.getenv("EVAL_CASE_IDS", "").split(",") if item}
    if requested_ids:
        cases = [case for case in cases if case["case_id"] in requested_ids]
    concurrency = max(1, int(os.getenv("EVAL_CONCURRENCY", "3")))
    deck = {card.id: card for card in build_deck()}
    gate = asyncio.Semaphore(concurrency)

    async def run_case(case: dict) -> tuple[dict, dict | None, dict]:
        async with gate:
            data = await make_reading(cfg, case, deck)
            return case, data, score_result(case, data)

    completed = await asyncio.gather(*(run_case(case) for case in cases))
    public_results, private_results = [], []
    for case, data, scored in completed:
        public_results.append({"case_id": case["case_id"], "lang": case["lang"], "spread": case["spread"], "profile": case["profile"], **scored})
        private_results.append({"case": case, "result": data, "evaluation": scored})
        print(f"{case['case_id']} {scored['status']}", flush=True)

    structured = [item for item in public_results if item["status"] == "llm_structured"]
    check_names = ("card_count", "all_cards_have_core_and_context", "has_synthesis", "has_practical_focus", "has_reflection_question", "share_safe_no_question_echo", "natural_output_length", "mystical_imagery_present", "no_gibberish_markers")
    public = {
        "prompt_version": PROMPT_VERSION,
        "fixture_cases": len(cases),
        "structured_cases": len(structured),
        "fallback_or_none_cases": len(cases) - len(structured),
        "hard_fail_cases": [item["case_id"] for item in public_results if item.get("hard_fail")],
        "check_failures": {name: sum(not item.get("checks", {}).get(name, False) for item in structured) for name in check_names},
        "results": public_results,
        "note": "Inputs are synthetic. Public output excludes raw questions and readings; private owner review is synthetic only.",
    }
    PUBLIC_OUTPUT.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
    PRIVATE_OUTPUT.write_text(json.dumps({"prompt_version": PROMPT_VERSION, "items": private_results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(PUBLIC_OUTPUT), "fixture_cases": len(cases), "structured": len(structured), "fallback": len(cases) - len(structured), "hard_fails": len(public["hard_fail_cases"])}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
