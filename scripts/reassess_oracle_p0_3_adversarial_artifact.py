from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from bot.tarot.deck import build_deck
from run_oracle_p0_3_adversarial_eval import assess_visible_payload, build_drawn

SOURCE_PUBLIC = ROOT / "docs" / "ORACLE_P0_3_ADVERSARIAL_PUBLIC_RESULTS.json"
SOURCE_PRIVATE = ROOT / "docs" / "ORACLE_P0_3_ADVERSARIAL_OWNER_REVIEW_PRIVATE.json"
OUTPUT = ROOT / "docs" / "ORACLE_P0_3_ADVERSARIAL_REASSESSMENT_PUBLIC_RESULTS.json"
SHA256_OUTPUT = ROOT / "docs" / "ORACLE_P0_3_ADVERSARIAL_REASSESSMENT_PUBLIC_RESULTS.sha256"


def main() -> None:
    public_source = json.loads(SOURCE_PUBLIC.read_text(encoding="utf-8"))
    private_source = json.loads(SOURCE_PRIVATE.read_text(encoding="utf-8"))
    deck = {card.id: card for card in build_deck()}
    results = []
    for item in private_source["items"]:
        case = item["case"]
        mode = item["mode"]
        if mode == "failed_to_complete" or not item.get("result"):
            results.append(
                {
                    "case_id": case["case_id"],
                    "category": case["category"],
                    "lang": case["lang"],
                    "spread": case["spread"],
                    "status": "failed_to_complete",
                    "pass": False,
                    "checks": {},
                    "error_category": "execution_error",
                }
            )
            continue
        drawn = build_drawn(case, deck)
        assessment = assess_visible_payload(case, drawn, item["result"], mode)
        results.append(
            {
                "case_id": case["case_id"],
                "category": case["category"],
                "lang": case["lang"],
                "spread": case["spread"],
                "status": mode,
                **assessment,
            }
        )

    status_counts = {
        status: sum(item["status"] == status for item in results)
        for status in ("structured", "deterministic_fallback", "failed_to_complete")
    }
    reassessment = {
        "source_run_id": public_source["run_id"],
        "source_public_artifact_sha256": hashlib.sha256(SOURCE_PUBLIC.read_bytes()).hexdigest(),
        "reassessment_timestamp_utc": datetime.now(UTC).isoformat(),
        "reassessment_reason": "P0-3 fallback draw check aligned with deterministic fallback fields actually rendered: position label, position meaning and orientation. Provider outputs were not re-run or modified.",
        "provider_execution_commit_sha": public_source["commit_sha"],
        "primary_model": public_source["primary_model"],
        "backup_model": public_source["backup_model"],
        "config_fingerprint": public_source["config_fingerprint"],
        "fixture_case_ids": public_source["fixture_case_ids"],
        "status_counts": status_counts,
        "contract_pass_cases": sum(item["pass"] for item in results),
        "contract_fail_cases": [item["case_id"] for item in results if not item["pass"]],
        "results": results,
        "note": "All inputs were synthetic. This public reassessment contains only non-secret metadata, case IDs, statuses and boolean checks. Raw synthetic outputs remain in the pre-existing owner-only artifact.",
    }
    OUTPUT.write_text(json.dumps(reassessment, ensure_ascii=False, indent=2), encoding="utf-8")
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    SHA256_OUTPUT.write_text(f"{digest}  {OUTPUT.name}\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "artifact_sha256": digest, "status_counts": status_counts, "contract_fail_cases": reassessment["contract_fail_cases"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
