from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path

from openai import AsyncOpenAI
from bot.config import load_config


def key_meta(value: str | None) -> dict:
    value = value or ""
    return {
        "present": bool(value),
        "length": len(value),
        "starts_with_sk": value.startswith("sk-"),
        "has_whitespace": value != value.strip(),
        "fingerprint": hashlib.sha256(value.encode()).hexdigest()[:12] if value else None,
    }


async def main() -> None:
    cfg = load_config(require_token=False)
    env_value = os.getenv("OPENROUTER_API_KEY", "")
    print({"base": cfg.llm_base_url, "primary": cfg.llm_model, "backup": cfg.llm_backup_model, "cfg_key": key_meta(cfg.openrouter_api_key), "process_env_key": key_meta(env_value)})
    client = AsyncOpenAI(base_url=cfg.llm_base_url, api_key=cfg.openrouter_api_key)
    for model in [cfg.llm_model, cfg.llm_backup_model]:
        if not model:
            continue
        try:
            result = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Reply in one natural sentence: The reading begins with clarity."}],
                max_tokens=64,
            )
            message = result.choices[0].message if result.choices else None
            dumped = message.model_dump() if message else {}
            print({
                "model": model,
                "choices": len(result.choices),
                "content_nonempty": bool(dumped.get("content")),
                "reasoning_nonempty": bool(dumped.get("reasoning") or dumped.get("reasoning_content")),
                "finish_reason": result.choices[0].finish_reason if result.choices else None,
            })
        except Exception as exc:  # metadata only
            print({"model": model, "error_type": type(exc).__name__, "error": str(exc)[:160]})


if __name__ == "__main__":
    asyncio.run(main())
