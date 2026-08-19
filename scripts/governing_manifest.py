from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


TERMINAL_MODES = {"llm_structured", "deterministic_fallback", "failed_to_complete"}
TERMINAL_STATUSES = {
    "COMPLETE",
    "BLOCKED_PROVIDER_RELIABILITY",
    "FAILED_CONTRACT",
}
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


class ManifestValidationError(RuntimeError):
    """A governing manifest or its bound artifacts failed closed validation."""


@dataclass(frozen=True)
class BoundManifest:
    path: Path
    data: dict
    run_dir: Path
    patch_path: Path
    fixture_path: Path
    critical_paths: dict[str, Path]
    application_db_path: Path
    run_db_path: Path
    public_output: Path
    private_output: Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint_contract(contract: dict[str, object]) -> str:
    encoded = json.dumps(contract, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def git_value(repo_root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=repo_root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ManifestValidationError(f"cannot read candidate git identity: {' '.join(args)}") from exc


def _require_mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ManifestValidationError(f"{label} must be an object")
    return value


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{label} must be a non-empty string")
    return value


def _within(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ManifestValidationError(f"{label} escapes its allowed root") from exc
    return resolved


def _relative_path(base: Path, value: object, label: str) -> Path:
    raw = Path(_require_string(value, label))
    if raw.is_absolute():
        raise ManifestValidationError(f"{label} must be relative")
    return _within(base / raw, base, label)


def _load_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestValidationError(f"cannot read {label}") from exc
    return _require_mapping(value, label)


def _validate_candidate(candidate: dict, repo_root: Path, run_dir: Path) -> Path:
    expected_sha = _require_string(candidate.get("commit_sha"), "candidate commit_sha")
    if git_value(repo_root, "rev-parse", "HEAD") != expected_sha:
        raise ManifestValidationError("candidate commit hash mismatch")

    expected_branch = _require_string(candidate.get("branch"), "candidate branch")
    current_branch = git_value(repo_root, "branch", "--show-current")
    if current_branch and current_branch != expected_branch:
        raise ManifestValidationError("candidate branch mismatch")

    if candidate.get("path_base") != "manifest_dir":
        raise ManifestValidationError("candidate patch path_base must be manifest_dir")
    patch_path = _relative_path(
        run_dir, candidate.get("worktree_patch_path"), "candidate patch path"
    )
    if not patch_path.is_file():
        raise ManifestValidationError("candidate patch is missing")
    if sha256_file(patch_path) != _require_string(
        candidate.get("worktree_patch_sha256"), "candidate patch sha256"
    ):
        raise ManifestValidationError("candidate patch hash mismatch")
    return patch_path


def _validate_fixture(fixture: dict, repo_root: Path) -> tuple[Path, list[str]]:
    fixture_path = _relative_path(repo_root, fixture.get("path"), "fixture path")
    if not fixture_path.is_file():
        raise ManifestValidationError("fixture is missing")
    if sha256_file(fixture_path) != _require_string(fixture.get("sha256"), "fixture sha256"):
        raise ManifestValidationError("fixture hash mismatch")
    try:
        cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestValidationError("fixture is not valid JSON") from exc
    if not isinstance(cases, list) or not cases:
        raise ManifestValidationError("fixture must contain a non-empty case list")
    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(case_ids) != len(cases) or any(not isinstance(case_id, str) for case_id in case_ids):
        raise ManifestValidationError("fixture case IDs are incomplete")
    if len(set(case_ids)) != len(case_ids):
        raise ManifestValidationError("fixture case IDs must be unique")
    if fixture.get("case_count") != len(cases) or fixture.get("case_ids") != case_ids:
        raise ManifestValidationError("fixture case binding mismatch")
    return fixture_path, case_ids


def _validate_critical_files(value: object, repo_root: Path) -> dict[str, Path]:
    hashes = _require_mapping(value, "critical_file_sha256")
    if not hashes:
        raise ManifestValidationError("critical file hash set must not be empty")
    paths: dict[str, Path] = {}
    for relative, expected_hash in hashes.items():
        if not isinstance(relative, str):
            raise ManifestValidationError("critical file path must be a string")
        path = _relative_path(repo_root, relative, f"critical file {relative}")
        if not path.is_file():
            raise ManifestValidationError(f"critical file is missing: {relative}")
        if sha256_file(path) != _require_string(expected_hash, f"critical hash {relative}"):
            raise ManifestValidationError(f"critical file hash mismatch: {relative}")
        paths[relative] = path
    return paths


def _validate_database(value: object, repo_root: Path, run_dir: Path) -> tuple[Path, Path]:
    database = _require_mapping(value, "database")
    application_raw = Path(
        _require_string(database.get("application_db_path"), "application database path")
    )
    application_path = (
        application_raw.resolve()
        if application_raw.is_absolute()
        else (repo_root / application_raw).resolve()
    )
    if database.get("path_base") != "manifest_dir":
        raise ManifestValidationError("run database path_base must be manifest_dir")
    run_path = _relative_path(
        run_dir, database.get("run_scoped_db_path"), "run database path"
    )
    if run_path == application_path:
        raise ManifestValidationError("governing evaluator resolved to the application database")
    if database.get("fail_closed_on_application_db_overlap") is not True:
        raise ManifestValidationError("database overlap guard must be enabled")
    return application_path, run_path


def _validate_outputs(value: object, run_dir: Path) -> tuple[Path, Path]:
    outputs = _require_mapping(value, "output_paths")
    if outputs.get("path_base") != "manifest_dir":
        raise ManifestValidationError("output path_base must be manifest_dir")
    public_path = _relative_path(run_dir, outputs.get("public"), "public output path")
    private_path = _relative_path(
        run_dir, outputs.get("private_owner_review"), "private output path"
    )
    if public_path == private_path:
        raise ManifestValidationError("public and private outputs must be distinct")
    return public_path, private_path


def load_and_validate_manifest(
    manifest_path: Path,
    *,
    repo_root: Path,
    current_contract: dict[str, object],
    require_planned: bool = True,
    require_outputs_absent: bool = False,
) -> BoundManifest:
    path = manifest_path.expanduser().resolve()
    if not path.is_file() or path.name != "manifest_v2.json":
        raise ManifestValidationError("manifest path must name an existing manifest_v2.json")
    data = _load_json(path, "manifest")
    if data.get("schema_version") != 2:
        raise ManifestValidationError("unsupported manifest schema_version")
    run_id = _require_string(data.get("run_id"), "run_id")
    if RUN_ID_PATTERN.fullmatch(run_id) is None or path.parent.name != run_id:
        raise ManifestValidationError("manifest run_id/path binding mismatch")
    if data.get("artifact_path_base") != "manifest_dir":
        raise ManifestValidationError("artifact_path_base must be manifest_dir")

    if require_planned and data.get("terminal_status") != "PLANNED":
        raise ManifestValidationError("manifest is already terminalized")
    final_binding = _require_mapping(data.get("final_output_binding"), "final_output_binding")
    if require_planned and any(
        final_binding.get(key) is not None for key in ("public_sha256", "private_sha256")
    ):
        raise ManifestValidationError("planned manifest already contains final output hashes")

    run_dir = path.parent.resolve()
    candidate = _require_mapping(data.get("canonical_candidate"), "canonical_candidate")
    patch_path = _validate_candidate(candidate, repo_root, run_dir)
    fixture = _require_mapping(data.get("fixture"), "fixture")
    fixture_path, _ = _validate_fixture(fixture, repo_root)
    critical_paths = _validate_critical_files(data.get("critical_file_sha256"), repo_root)

    response_contract = _require_mapping(data.get("response_contract"), "response_contract")
    if response_contract != current_contract:
        raise ManifestValidationError("response contract mismatch")
    expected_fingerprint = fingerprint_contract(current_contract)
    if data.get("config_fingerprint_sha256") != expected_fingerprint:
        raise ManifestValidationError("config fingerprint mismatch")

    application_db, run_db = _validate_database(data.get("database"), repo_root, run_dir)
    public_output, private_output = _validate_outputs(data.get("output_paths"), run_dir)
    if require_outputs_absent and (public_output.exists() or private_output.exists()):
        raise ManifestValidationError("planned output artifact already exists")

    return BoundManifest(
        path=path,
        data=data,
        run_dir=run_dir,
        patch_path=patch_path,
        fixture_path=fixture_path,
        critical_paths=critical_paths,
        application_db_path=application_db,
        run_db_path=run_db,
        public_output=public_output,
        private_output=private_output,
    )


def validate_output_documents(manifest: dict, public: dict, private: dict) -> str:
    run_id = manifest["run_id"]
    case_ids = manifest["fixture"]["case_ids"]
    if public.get("run_id") != run_id or private.get("run_id") != run_id:
        raise ManifestValidationError("output run_id mismatch")
    if public.get("fixture_cases") != len(case_ids) or public.get("case_ids") != case_ids:
        raise ManifestValidationError("public output fixture binding mismatch")

    results = public.get("results")
    if not isinstance(results, list) or [item.get("case_id") for item in results] != case_ids:
        raise ManifestValidationError("public output is incomplete or reordered")
    modes = [item.get("status") for item in results]
    if any(mode not in TERMINAL_MODES for mode in modes):
        raise ManifestValidationError("public output contains a non-terminal case")
    expected_counts = {mode: modes.count(mode) for mode in TERMINAL_MODES}
    if public.get("terminal_mode_counts") != expected_counts:
        raise ManifestValidationError("terminal mode counts do not match results")

    counterparts = public.get("fallback_counterparts")
    if not isinstance(counterparts, list) or [item.get("case_id") for item in counterparts] != case_ids:
        raise ManifestValidationError("fallback counterpart output is incomplete or reordered")

    items = private.get("items")
    if not isinstance(items, list) or len(items) != len(case_ids):
        raise ManifestValidationError("private owner output is incomplete")
    private_ids: list[object] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("case"), dict):
            raise ManifestValidationError("private owner output item is malformed")
        private_ids.append(item["case"].get("case_id"))
        if item.get("delivery_mode") not in TERMINAL_MODES:
            raise ManifestValidationError("private owner output contains a non-terminal case")
    if private_ids != case_ids:
        raise ManifestValidationError("private owner output is incomplete or reordered")

    if any(item.get("hard_fail") for item in results) or public.get("contract_fail_cases"):
        expected_status = "FAILED_CONTRACT"
    elif expected_counts["failed_to_complete"]:
        expected_status = "BLOCKED_PROVIDER_RELIABILITY"
    else:
        expected_status = "COMPLETE"
    if public.get("terminal_status") != expected_status:
        raise ManifestValidationError("public terminal status does not match case outcomes")
    return expected_status


def validate_output_artifacts(bound: BoundManifest) -> str:
    if not bound.public_output.is_file() or not bound.private_output.is_file():
        raise ManifestValidationError("both required output artifacts must exist")
    public = _load_json(bound.public_output, "public output")
    private = _load_json(bound.private_output, "private owner output")
    return validate_output_documents(bound.data, public, private)


def _write_json_atomic(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def terminalize_manifest(
    manifest_path: Path,
    *,
    repo_root: Path,
    current_contract: dict[str, object],
    requested_status: str | None = None,
) -> str:
    bound = load_and_validate_manifest(
        manifest_path,
        repo_root=repo_root,
        current_contract=current_contract,
        require_planned=True,
        require_outputs_absent=False,
    )
    actual_status = validate_output_artifacts(bound)
    if requested_status is not None and requested_status != actual_status:
        raise ManifestValidationError("requested terminal status conflicts with verified outputs")

    refreshed = _load_json(bound.path, "manifest")
    if refreshed.get("terminal_status") != "PLANNED":
        raise ManifestValidationError("manifest terminal state changed during finalization")
    refreshed["terminal_status"] = actual_status
    refreshed["terminalized_at_utc"] = datetime.now(UTC).isoformat()
    refreshed["final_output_binding"]["public_sha256"] = sha256_file(bound.public_output)
    refreshed["final_output_binding"]["private_sha256"] = sha256_file(bound.private_output)
    _write_json_atomic(bound.path, refreshed)
    return actual_status


__all__ = [
    "BoundManifest",
    "ManifestValidationError",
    "TERMINAL_MODES",
    "TERMINAL_STATUSES",
    "fingerprint_contract",
    "git_value",
    "load_and_validate_manifest",
    "sha256_file",
    "terminalize_manifest",
    "validate_output_artifacts",
    "validate_output_documents",
]
