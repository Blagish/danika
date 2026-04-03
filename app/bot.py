import traceback

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
    """Best girl."""

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

        if config.run_mode == "dev" and config.dev_guild_id:
            guild = discord.Object(id=config.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Slash commands synced to dev guild {config.dev_guild_id}")
        else:
            await self.tree.sync()
            logger.info("Slash commands synced globally")

    async def on_ready(self) -> None:
        logger.info(
            f"Logged in as {self.user} (ID: {self.user.id if self.user else 'unknown'})"
        )

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        if hasattr(ctx.command, "on_error"):
            return

        error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound):
            return

        logger.error(f"Error in command {ctx.command}: {error}")

        if config.run_mode == "dev":
            tb = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            await ctx.reply(f"```\n{tb[:1900]}\n```", ephemeral=True)
        else:
            await ctx.reply("Что-то пошло не так.", ephemeral=True)
