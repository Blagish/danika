from discord import app_commands
from discord.ext import commands

from app.dice import roll
from app.formatters.dice import RollResponse
from app.i18n import ARG_ROLL_EXPRESSION, CMD_ROLL


class Dice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="roll",
        aliases=["r", "р"],
        description=CMD_ROLL,
    )
    @app_commands.describe(expression=ARG_ROLL_EXPRESSION)
    async def roll(self, ctx: commands.Context, *, expression: str) -> None:
        try:
            results = roll(expression)
            response = str(RollResponse.from_rolls(results, expression))
            await ctx.reply(response)
        except ValueError as e:
            await ctx.reply(str(e), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Dice(bot))
