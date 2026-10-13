from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv

from quadton.bot import Quadton
from quadton.config import Config
from quadton.db.database import Database
from quadton.logging_setup import configure


async def main() -> None:
    load_dotenv()
    configure(os.environ.get("QUADTON_LOG_LEVEL", "INFO"))
    log = logging.getLogger("quadton")
    try:
        config = Config.from_env()
    except RuntimeError as exc:
        log.error("Configuration error: %s", exc)
        raise SystemExit(1)

    db = Database(config.database_path)
    await db.connect()

    bot = Quadton(config, db)
    try:
        await bot.start(config.discord_token)
    finally:
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
