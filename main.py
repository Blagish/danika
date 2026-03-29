import asyncio

import discord
from loguru import logger

from app.bot import Danika
from app.config import get_config

config = get_config()


async def main() -> None:
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
