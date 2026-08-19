from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.db.database import ALEMBIC_HEAD


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest() -> dict:
    status = _git("status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise RuntimeError("release artifact manifest requires a clean worktree")
    tracked = [line for line in _git("ls-files").splitlines() if line]
    files = []
    for relative in tracked:
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"tracked release file is missing: {relative}")
        files.append(
            {
                "path": relative.replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "candidate_sha": _git("rev-parse", "HEAD"),
        "candidate_tree_sha": _git("rev-parse", "HEAD^{tree}"),
        "branch": _git("branch", "--show-current") or "DETACHED",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "alembic_head": ALEMBIC_HEAD,
        "tracked_file_count": len(files),
        "tracked_files": files,
    }


def write_manifest(output: Path) -> str:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(build_manifest(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(output)
    digest = _sha256(output)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.name}\n", encoding="ascii"
    )
    return digest


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a sanitized exact-SHA release manifest.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    try:
        digest = write_manifest(output)
    except RuntimeError as exc:
        parser.error(str(exc))
        return
    print(
        json.dumps(
            {
                "output": str(output.expanduser().resolve()),
                "candidate_sha": _git("rev-parse", "HEAD"),
                "sha256": digest,
            }
        )
    )


if __name__ == "__main__":
    main()
