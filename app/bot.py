import discord
from discord.ext import commands
from loguru import logger

from app.config import get_config
from app.i18n import DanikaTranslator

_log = logger.bind(module=__name__)

config = get_config()

COGS: list[str] = [
    "app.cogs.general",
    "app.cogs.dice",
    "app.cogs.status",
    "app.cogs.systems",
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
            _log.debug(f"Loaded cog: {cog}")

        await self.tree.set_translator(DanikaTranslator())

        if config.run_mode == "dev" and config.dev_guild_id:
            guild = discord.Object(id=config.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            _log.info(f"Slash commands synced to dev guild {config.dev_guild_id}")
        else:
            await self.tree.sync()
            _log.info("Slash commands synced globally")

    async def on_ready(self) -> None:
        _log.info(f"Logged in as {self.user} (ID: {self.user.id if self.user else 'unknown'})")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if hasattr(ctx.command, "on_error"):
            return

        error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound):
            return

        with logger.catch(reraise=False):
            raise error

        if config.run_mode == "dev":
            await ctx.reply(f"```\n{type(error).__name__}: {error}\n```", ephemeral=True)
        else:
            await ctx.reply("Что-то пошло не так.", ephemeral=True)
