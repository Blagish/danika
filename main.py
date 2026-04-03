import asyncio
import sys

import discord
from loguru import logger

from app.bot import Danika
from app.config import get_config

config = get_config()


def setup_logging() -> None:
    logger.remove()
    level = "DEBUG" if config.run_mode == "dev" else "INFO"
    logger.add(sys.stderr, level=level)


async def main() -> None:
    setup_logging()
    async with Danika() as bot:
        try:
            await bot.start(config.discord_token)
        except discord.LoginFailure:
            logger.error("Invalid Discord token")
            raise SystemExit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
