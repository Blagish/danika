import discord
from discord.ext import commands
from loguru import logger

from app.config import get_config

config = get_config()

COGS: list[str] = [
    "app.cogs.general",
    "app.cogs.dice",
]


class Danika(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(config.command_prefix),
            intents=intents,
        )

    async def setup_hook(self) -> None:
        for cog in COGS:
            await self.load_extension(cog)
            logger.debug(f"Loaded cog: {cog}")

        await self.tree.sync()
        logger.info("Slash commands synced")

    async def on_ready(self) -> None:
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
