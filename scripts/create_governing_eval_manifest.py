from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.config import Config, load_config
from bot.llm.adapter import PROMPT_VERSION
from scripts.governing_manifest import (
    RUN_ID_PATTERN,
    TERMINAL_STATUSES,
    ManifestValidationError,
    fingerprint_contract,
    git_value,
    sha256_file,
    terminalize_manifest,
)


FIXTURE_PATH = ROOT / "tests" / "fixtures" / "quality_eval_24.json"
CRITICAL_FILES = (
    "bot/llm/adapter.py",
    "bot/tarot/fallback.py",
    "scripts/governing_manifest.py",
    "scripts/create_governing_eval_manifest.py",
    "scripts/run_oracle_v6_eval.py",
    "scripts/run_oracle_v6_eval_parallel.py",
    "tests/test_governing_eval_candidate_b_contract.py",
    "tests/test_governing_eval_candidate_c_contract.py",
    "tests/test_sol_oracle_gate_regressions.py",
    "tests/test_oracle_eval_spread_contract.py",
    "tests/test_llm_schema.py",
)


def response_contract(cfg: Config) -> dict[str, object]:
    """Return the complete non-secret provider and prompt execution contract."""
    return {
        "primary_model": cfg.llm_model,
        "backup_model": cfg.llm_backup_model,
        "base_url": cfg.llm_base_url,
        "json_mode": cfg.llm_json_mode,
        "retry_policy_v2": cfg.llm_retry_policy_v2,
        "controlled_repair_enabled": cfg.llm_controlled_repair_enabled,
        "v2_primary_timeout_seconds": cfg.llm_v2_primary_timeout_sec,
        "v2_total_timeout_seconds": cfg.llm_v2_total_timeout_sec,
        "v2_max_attempts": cfg.llm_v2_max_attempts,
        "legacy_timeout_seconds": 90,
        "temperature": 0.65,
        "max_tokens": 6000,
        "concurrency": 1,
        "prompt_version": PROMPT_VERSION,
    }


def new_run_id(candidate_id: str) -> str:
    normalized = candidate_id.lower().replace("_", "-")
    return f"{normalized}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"


def _write_json_atomic(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def create_manifest(
    candidate_id: str,
    patch_path: Path,
    *,
    output_root: Path,
    run_id: str | None = None,
) -> Path:
    source_patch = patch_path.expanduser().resolve()
    if not source_patch.is_file():
        raise ManifestValidationError(f"patch file does not exist: {source_patch}")
    selected_run_id = run_id or new_run_id(candidate_id)
    if RUN_ID_PATTERN.fullmatch(selected_run_id) is None:
        raise ManifestValidationError("run_id contains unsupported characters")

    run_dir = output_root.expanduser().resolve() / selected_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "manifest_v2.json"
    if manifest_path.exists():
        raise ManifestValidationError("manifest already exists for this run_id")

    bundled_patch = run_dir / "candidate.patch"
    if source_patch != bundled_patch:
        if bundled_patch.exists():
            raise ManifestValidationError("candidate.patch already exists in the run directory")
        shutil.copyfile(source_patch, bundled_patch)

    cfg = load_config(require_token=False)
    contract = response_contract(cfg)
    fixture_cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case_ids = [case["case_id"] for case in fixture_cases]
    branch = git_value(ROOT, "branch", "--show-current") or "DETACHED"

    missing_critical = [relative for relative in CRITICAL_FILES if not (ROOT / relative).is_file()]
    if missing_critical:
        raise ManifestValidationError(
            "critical files are missing: " + ", ".join(missing_critical)
        )

    application_db = Path(cfg.db_path).expanduser()
    if not application_db.is_absolute():
        application_db = (ROOT / application_db).resolve()
    manifest = {
        "schema_version": 2,
        "candidate_id": candidate_id,
        "run_id": selected_run_id,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "terminal_status": "PLANNED",
        "artifact_path_base": "manifest_dir",
        "canonical_candidate": {
            "commit_sha": git_value(ROOT, "rev-parse", "HEAD"),
            "branch": branch,
            "path_base": "manifest_dir",
            "worktree_patch_path": bundled_patch.name,
            "worktree_patch_sha256": sha256_file(bundled_patch),
        },
        "fixture": {
            "path": FIXTURE_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(FIXTURE_PATH),
            "case_count": len(fixture_cases),
            "case_ids": case_ids,
        },
        "critical_file_sha256": {
            relative: sha256_file(ROOT / relative) for relative in CRITICAL_FILES
        },
        "response_contract": contract,
        "config_fingerprint_sha256": fingerprint_contract(contract),
        "database": {
            "application_db_path": str(application_db),
            "path_base": "manifest_dir",
            "run_scoped_db_path": "governing-eval.db",
            "fail_closed_on_application_db_overlap": True,
        },
        "output_paths": {
            "path_base": "manifest_dir",
            "public": "actual_delivery_public.json",
            "private_owner_review": "actual_delivery_owner_review_private.json",
        },
        "final_output_binding": {
            "public_sha256": None,
            "private_sha256": None,
            "written_only_after_all_terminal_modes": True,
        },
        "note": (
            "Non-secret manifest. It remains PLANNED until the canonical evaluator validates "
            "every bound input and required output, then terminalizes this same file."
        ),
    }
    _write_json_atomic(manifest_path, manifest)
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or independently verify terminalization of a governing Manifest-v2."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--candidate-id", required=True)
    create.add_argument("--patch", required=True)
    create.add_argument("--output-root", default=str(ROOT / "docs" / "governing_runs"))
    create.add_argument("--run-id")
    finalize = subparsers.add_parser("finalize")
    finalize.add_argument("--manifest", required=True)
    finalize.add_argument("--terminal-status", choices=sorted(TERMINAL_STATUSES))
    args = parser.parse_args()

    try:
        if args.command == "create":
            manifest_path = create_manifest(
                args.candidate_id,
                Path(args.patch),
                output_root=Path(args.output_root),
                run_id=args.run_id,
            )
            result = {
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "run_id": manifest_path.parent.name,
                "terminal_status": "PLANNED",
            }
        else:
            cfg = load_config(require_token=False)
            status = terminalize_manifest(
                Path(args.manifest),
                repo_root=ROOT,
                current_contract=response_contract(cfg),
                requested_status=args.terminal_status,
            )
            manifest_path = Path(args.manifest).resolve()
            result = {
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "terminal_status": status,
            }
    except ManifestValidationError as exc:
        parser.error(str(exc))
        return
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
