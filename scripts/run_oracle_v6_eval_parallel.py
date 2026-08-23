from __future__ import annotations

import asyncio
import os

from run_oracle_v6_eval import main as run_governing_eval


async def main() -> None:
    """Compatibility entry point for the former parallel evaluator.

    The locked governing contract requires one run-scoped SQLite database and
    deterministic terminal accounting.  This compatibility wrapper therefore
    delegates to the canonical serial runner and rejects a request for parallel
    execution rather than creating a second semantics path.
    """
    concurrency = int(os.getenv("EVAL_CONCURRENCY", "1"))
    if concurrency != 1:
        raise SystemExit(
            "The governing evaluator requires EVAL_CONCURRENCY=1; use the canonical serial path."
        )
    await run_governing_eval()


if __name__ == "__main__":
    asyncio.run(main())
