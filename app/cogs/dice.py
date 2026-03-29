from discord import app_commands
from discord.ext import commands

from app.dice import RollResult, roll


def format_result(result: RollResult) -> str:
    rolls_str = ", ".join(str(r) for r in result.rolls)
    parts = [f"🎲 **{result.expression}**"]
    if rolls_str:
        parts.append(f"[{rolls_str}]")
    parts.append(f"= **{result.total}**")
    return " ".join(parts)


class Dice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="roll",
        aliases=["r", "р"],
        description="Бросить кубы. Пример: д20+3, 2*(д6+1)",
    )
    @app_commands.describe(
        expression="Выражение броска, например: д20+3, 2д6, 3*(d8+2)"
    )
    async def roll(self, ctx: commands.Context, *, expression: str) -> None:
        try:
            result = roll(expression)
            await ctx.reply(format_result(result))
        except ValueError as e:
            await ctx.reply(str(e), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Dice(bot))
