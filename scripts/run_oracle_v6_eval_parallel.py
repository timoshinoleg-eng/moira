from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_oracle_v6_eval import cli_main


def main() -> None:
    """Retain one governing semantics path and reject parallel provider execution."""
    concurrency = int(os.getenv("EVAL_CONCURRENCY", "1"))
    if concurrency != 1:
        raise SystemExit(
            "The governing evaluator requires EVAL_CONCURRENCY=1; use the canonical serial path."
        )
    cli_main()


if __name__ == "__main__":
    main()
