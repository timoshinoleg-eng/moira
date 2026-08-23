from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openai import AsyncOpenAI

from bot.config import load_config


async def main() -> None:
    model = os.getenv("OPENROUTER_SMOKE_MODEL", "").strip()
    if not model:
        raise SystemExit("Set OPENROUTER_SMOKE_MODEL to one specific candidate before running this smoke check.")

    cfg = load_config(require_token=False)
    if not cfg.openrouter_api_key:
        raise SystemExit("OpenRouter API key is not configured.")

    client = AsyncOpenAI(base_url=cfg.llm_base_url, api_key=cfg.openrouter_api_key, timeout=90.0)
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Return only a JSON object. Do not include markdown or prose.",
                },
                {
                    "role": "user",
                    "content": "Return exactly {\"status\":\"backup-json-smoke-pass\",\"language\":\"en\"}.",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=128,
        )
        content = response.choices[0].message.content if response.choices else ""
        parsed = json.loads(content or "")
        valid = isinstance(parsed, dict) and parsed.get("status") == "backup-json-smoke-pass"
        print(
            json.dumps(
                {
                    "candidate": model,
                    "served_model": getattr(response, "model", None),
                    "finish_reason": response.choices[0].finish_reason if response.choices else None,
                    "content_nonempty": bool(content),
                    "valid_json_contract": valid,
                },
                ensure_ascii=False,
            )
        )
        if not valid:
            raise SystemExit(2)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "candidate": model,
                    "error_type": type(exc).__name__,
                    "error_category": "provider_or_validation_error",
                },
                ensure_ascii=False,
            )
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    asyncio.run(main())
