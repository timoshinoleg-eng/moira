import asyncio, logging, sys
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr)
from bot.config import load_config
from bot.db import init_db
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
async def t():
    cfg = load_config(require_token=True)
    print("cfg ok, model:", cfg.llm_model, cfg.llm_base_url, flush=True)
    await init_db(cfg.db_path)
    print("db ok", flush=True)
    bot = Bot(token=cfg.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    print("bot obj ok", flush=True)
    await bot.delete_webhook(drop_pending_updates=True)
    print("delete_webhook ok", flush=True)
    await bot.session.close()
asyncio.run(asyncio.wait_for(t(), timeout=45))
print("ALL OK", flush=True)
