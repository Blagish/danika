import asyncio
import contextlib

import discord
from loguru import logger

from app.bot import Danika
from app.config import get_config
from app.logging import setup_logging

config = get_config()


async def main() -> None:
    setup_logging()
    async with Danika() as bot:
        try:
            await bot.start(config.discord_token)
        except discord.LoginFailure:
            logger.error("Invalid Discord token")
            raise SystemExit(1) from None


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
