import discord
from discord import app_commands
from discord.ext import commands

from app.i18n import CMD_PING


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description=CMD_PING)
    async def ping(self, interaction: discord.Interaction) -> None:
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! `{latency}ms`")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
