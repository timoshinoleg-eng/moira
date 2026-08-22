from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openai import AsyncOpenAI

from bot.config import load_config


async def main() -> None:
    cfg = load_config(require_token=False)
    if not cfg.openrouter_api_key:
        raise SystemExit("OpenRouter API key is not configured.")

    client = AsyncOpenAI(base_url=cfg.llm_base_url, api_key=cfg.openrouter_api_key, timeout=30.0)
    try:
        response = await client.models.list()
        ids = sorted(
            model.id
            for model in response.data
            if isinstance(getattr(model, "id", None), str) and model.id.endswith(":free")
        )
        print(json.dumps({"free_model_ids": ids, "count": len(ids)}, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error_type": type(exc).__name__, "error_category": "provider_catalog_error"}, ensure_ascii=False))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    asyncio.run(main())
