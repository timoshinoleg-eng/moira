from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from bot.config import load_config
from bot.llm.adapter import (
    FORMAT_EN,
    FORMAT_RU,
    TarotReadingResult,
    validate_ordered_draw_identity,
)
from bot.tarot.deck import build_deck
from bot.tarot.spreads import DrawnCard, SPREADS
from scripts.create_governing_eval_manifest import create_manifest, response_contract
from scripts.governing_manifest import (
    ManifestValidationError,
    load_and_validate_manifest,
    terminalize_manifest,
)
from scripts.run_oracle_v6_eval import ROOT, run_manifest


def _planned_manifest(tmp_path: Path, run_id: str = "candidate-c-contract") -> Path:
    patch_path = tmp_path / "candidate-source.patch"
    patch_path.write_text("synthetic candidate patch\n", encoding="utf-8")
    return create_manifest(
        "CANDIDATE_C",
        patch_path,
        output_root=tmp_path,
        run_id=run_id,
    )


def _bound(manifest_path: Path, *, outputs_absent: bool = False):
    return load_and_validate_manifest(
        manifest_path,
        repo_root=ROOT,
        current_contract=response_contract(load_config(require_token=False)),
        require_planned=True,
        require_outputs_absent=outputs_absent,
    )


def _complete_documents(manifest: dict) -> tuple[dict, dict]:
    case_ids = manifest["fixture"]["case_ids"]
    results = [
        {
            "case_id": case_id,
            "status": "deterministic_fallback",
            "hard_fail": False,
            "checks": {"complete": True},
        }
        for case_id in case_ids
    ]
    public = {
        "run_id": manifest["run_id"],
        "fixture_cases": len(case_ids),
        "case_ids": case_ids,
        "terminal_status": "COMPLETE",
        "terminal_mode_counts": {
            "llm_structured": 0,
            "deterministic_fallback": len(case_ids),
            "failed_to_complete": 0,
        },
        "hard_fail_cases": [],
        "contract_fail_cases": [],
        "results": results,
        "fallback_counterparts": [{"case_id": case_id} for case_id in case_ids],
    }
    private = {
        "run_id": manifest["run_id"],
        "items": [
            {
                "case": {"case_id": case_id},
                "delivery_mode": "deterministic_fallback",
                "result": None,
            }
            for case_id in case_ids
        ],
    }
    return public, private


def _write_documents(bound, public: dict, private: dict) -> None:
    bound.public_output.write_text(
        json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    bound.private_output.write_text(
        json.dumps(private, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def test_direct_script_and_module_validate_the_same_planned_manifest_without_provider_calls(
    tmp_path: Path,
) -> None:
    manifest_path = _planned_manifest(tmp_path)
    script = ROOT / "scripts" / "run_oracle_v6_eval.py"
    direct = subprocess.run(
        [sys.executable, str(script), "--manifest", str(manifest_path), "--validate-only"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    module = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_oracle_v6_eval",
            "--manifest",
            str(manifest_path),
            "--validate-only",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert direct.returncode == 0, direct.stderr
    assert module.returncode == 0, module.stderr
    assert json.loads(direct.stdout)["provider_calls"] == 0
    assert json.loads(module.stdout)["provider_calls"] == 0
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["terminal_status"] == "PLANNED"
    assert not (manifest_path.parent / "governing-eval.db").exists()


def test_validate_only_never_enters_provider_path(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _planned_manifest(tmp_path)
    provider = AsyncMock(side_effect=AssertionError("provider path must remain unreachable"))
    monkeypatch.setattr("scripts.run_oracle_v6_eval.make_reading", provider)

    result = asyncio.run(run_manifest(manifest_path, validate_only=True))

    assert result["validation"] == "PASS"
    assert result["provider_calls"] == 0
    provider.assert_not_awaited()


def test_runner_terminalizes_the_same_manifest_after_complete_fallback_outputs(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY_FILE", raising=False)
    manifest_path = _planned_manifest(tmp_path, "candidate-c-runner-terminalization")
    provider_adapter = AsyncMock(return_value=None)
    monkeypatch.setattr("scripts.run_oracle_v6_eval.interpret_reading", provider_adapter)

    result = asyncio.run(run_manifest(manifest_path))

    finalized = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result["terminal_status"] == "COMPLETE"
    assert finalized["terminal_status"] == "COMPLETE"
    assert provider_adapter.await_count == finalized["fixture"]["case_count"]
    assert (manifest_path.parent / "actual_delivery_public.json").is_file()
    assert (manifest_path.parent / "actual_delivery_owner_review_private.json").is_file()


@pytest.mark.parametrize(
    "binding",
    ["candidate", "patch", "fixture", "config", "critical"],
)
def test_bound_hash_mismatch_is_rejected_before_provider_call(
    tmp_path: Path, monkeypatch, binding: str
) -> None:
    manifest_path = _planned_manifest(tmp_path, f"candidate-c-mismatch-{binding}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if binding == "candidate":
        manifest["canonical_candidate"]["commit_sha"] = "0" * 40
    elif binding == "patch":
        manifest["canonical_candidate"]["worktree_patch_sha256"] = "0" * 64
    elif binding == "fixture":
        manifest["fixture"]["sha256"] = "0" * 64
    elif binding == "config":
        manifest["config_fingerprint_sha256"] = "0" * 64
    else:
        first = next(iter(manifest["critical_file_sha256"]))
        manifest["critical_file_sha256"][first] = "0" * 64
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    provider = AsyncMock(side_effect=AssertionError("provider path must remain unreachable"))
    monkeypatch.setattr("scripts.run_oracle_v6_eval.make_reading", provider)

    with pytest.raises(ManifestValidationError, match="mismatch"):
        asyncio.run(run_manifest(manifest_path, validate_only=False))
    provider.assert_not_awaited()


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    manifest_path = _planned_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["output_paths"]["public"] = "../escaped.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(ManifestValidationError, match="escapes"):
        _bound(manifest_path)


def test_successful_terminalization_binds_both_output_hashes_and_rejects_refinalization(
    tmp_path: Path,
) -> None:
    manifest_path = _planned_manifest(tmp_path)
    bound = _bound(manifest_path, outputs_absent=True)
    public, private = _complete_documents(bound.data)
    _write_documents(bound, public, private)

    status = terminalize_manifest(
        manifest_path,
        repo_root=ROOT,
        current_contract=response_contract(load_config(require_token=False)),
        requested_status="COMPLETE",
    )

    finalized = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert status == "COMPLETE"
    assert finalized["terminal_status"] == "COMPLETE"
    assert len(finalized["final_output_binding"]["public_sha256"]) == 64
    assert len(finalized["final_output_binding"]["private_sha256"]) == 64
    with pytest.raises(ManifestValidationError, match="already terminalized"):
        terminalize_manifest(
            manifest_path,
            repo_root=ROOT,
            current_contract=response_contract(load_config(require_token=False)),
            requested_status="FAILED_CONTRACT",
        )


def test_incomplete_output_is_rejected_without_terminalizing_manifest(tmp_path: Path) -> None:
    manifest_path = _planned_manifest(tmp_path)
    bound = _bound(manifest_path, outputs_absent=True)
    public, private = _complete_documents(bound.data)
    public["results"].pop()
    _write_documents(bound, public, private)

    with pytest.raises(ManifestValidationError, match="incomplete or reordered"):
        terminalize_manifest(
            manifest_path,
            repo_root=ROOT,
            current_contract=response_contract(load_config(require_token=False)),
        )
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["terminal_status"] == "PLANNED"


def _ru_drawn() -> list[DrawnCard]:
    deck = {card.id: card for card in build_deck()}
    spread = SPREADS["situation"]
    specs = (("major_0", False), ("major_1", True), ("major_2", False))
    return [
        DrawnCard(
            position_id=position_id,
            position_label=labels,
            card=deck[card_id],
            reversed=reversed_value,
        )
        for (position_id, labels), (card_id, reversed_value) in zip(
            spread["positions"], specs
        )
    ]


def _reading_payload(drawn: list[DrawnCard]) -> dict:
    return {
        "headline": "Тихий и ясный поворот",
        "opening": "Карты показывают спокойный порог перемен и предлагают увидеть факты без спешки.",
        "card_interpretations": [
            {
                "position": card.position_label["ru"],
                "card_name": card.card.name("ru"),
                "orientation": "reversed" if card.reversed else "upright",
                "core_message": "Эта карта показывает конкретное напряжение и один полезный следующий шаг.",
                "symbolic_detail": "Свет у порога.",
                "context_connection": "Связь с проверяемым выбором.",
            }
            for card in drawn
        ],
        "synthesis": (
            "Общий рисунок расклада соединяет осторожность, наблюдение и действие. "
            "Порог здесь означает момент, когда полезно отделить предположение от факта, "
            "выбрать один небольшой шаг и проверить его результат до окончательного решения."
        ),
        "practical_focus": "Запишите один наблюдаемый факт и выполните один небольшой обратимый шаг сегодня.",
        "reflection_question": "Какой факт поможет выбрать следующий шаг спокойнее?",
        "voice_summary": (
            "Расклад предлагает не торопить вывод, заметить главное напряжение и проверить "
            "небольшой безопасный шаг, сохраняя право изменить решение после результата."
        ),
        "share_summary": "Полезно отделить факт от предположения и проверить один небольшой следующий шаг.",
    }


def test_ru_machine_orientation_accepts_canonical_upright_and_reversed() -> None:
    drawn = _ru_drawn()
    result = TarotReadingResult.model_validate(_reading_payload(drawn))

    validate_ordered_draw_identity(result, drawn, "ru")
    assert [item.orientation for item in result.card_interpretations] == [
        "upright",
        "reversed",
        "upright",
    ]


def test_localized_orientation_is_rejected_at_machine_schema_boundary() -> None:
    payload = _reading_payload(_ru_drawn())
    payload["card_interpretations"][0]["orientation"] = "прямая"

    with pytest.raises(ValidationError):
        TarotReadingResult.model_validate(payload)


def test_both_prompt_contracts_freeze_the_same_machine_orientation_enum() -> None:
    for contract in (FORMAT_RU, FORMAT_EN):
        assert '"upright"' in contract
        assert '"reversed"' in contract
