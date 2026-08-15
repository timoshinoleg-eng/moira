from __future__ import annotations

import json
from pathlib import Path


FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "quality_eval_24.json"


def test_quality_fixture_has_24_unique_cases_and_full_coverage() -> None:
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(rows) == 24
    assert len({row["case_id"] for row in rows}) == 24
    assert {row["lang"] for row in rows} == {"ru", "en"}
    assert len([row for row in rows if row["lang"] == "ru"]) == 12
    assert len([row for row in rows if row["lang"] == "en"]) == 12
    assert {row["spread"] for row in rows} == {"situation", "love", "choice"}
    assert {row["profile"] for row in rows} == {"decision", "relationship", "work", "inner_change"}
    assert not any(row["hard_fail"] for row in rows)
    assert all(row["has_card_grounding"] for row in rows)
    assert all(row["has_synthesis"] and row["has_reflection"] for row in rows)
