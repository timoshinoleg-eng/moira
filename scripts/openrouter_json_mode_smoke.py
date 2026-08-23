from __future__ import annotations

import asyncio
from openai import AsyncOpenAI
from bot.config import load_config

CANDIDATES = (
    "nvidia/nemotron-3-super-120b-a12b:free",
    "liquid/lfm-2.5-2.6b:free",
    "google/gemma-4-31b-it:free",
    "dots-studio/dots-3-note-preview:free",
)


async def main() -> None:
    cfg = load_config(require_token=False)
    client = AsyncOpenAI(base_url=cfg.llm_base_url, api_key=cfg.openrouter_api_key)
    for model in CANDIDATES:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Return only JSON: {\"status\":\"oracle-json-pass\",\"note\":\"clear\"}"}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=128,
            )
            content = response.choices[0].message.content if response.choices else ""
            print({"model": model, "content_nonempty": bool(content), "json_like": bool(content and content.strip().startswith("{")), "finish_reason": response.choices[0].finish_reason if response.choices else None})
        except Exception as exc:
            print({"model": model, "error_type": type(exc).__name__, "error": str(exc)[:160]})


if __name__ == "__main__":
    asyncio.run(main())
