import random
from pathlib import Path

import discord
from discord.ext import commands, tasks

_DATA_DIR = Path(__file__).parent.parent / "data" / "status"


def _load_lines(filename: str) -> list[str]:
    """Загружает непустые строки из файла данных."""
    path = _DATA_DIR / filename
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


class Status(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.systems = _load_lines("ttrpg_systems.txt")
        self.templates = _load_lines("status_templates.txt")

    async def cog_load(self) -> None:
        self.rotate_status.start()

    async def cog_unload(self) -> None:
        self.rotate_status.cancel()

    async def _set_random_status(self) -> str:
        """Применяет случайный статус. Возвращает итоговую строку."""
        template = random.choice(self.templates)
        system = random.choice(self.systems)
        name = template.format(system=system, session=random.randint(2, 100))
        await self.bot.change_presence(activity=discord.Game(name=name))
        return name

    @tasks.loop(hours=7)
    async def rotate_status(self) -> None:
        await self._set_random_status()
        self.rotate_status.change_interval(hours=random.uniform(6, 8))

    @commands.command(name="reroll-status")
    @commands.is_owner()
    async def reroll_status(self, ctx: commands.Context) -> None:
        """Меняет статус на случайный. Только для владельца бота."""
        name = await self._set_random_status()
        await ctx.reply(f"Статус обновлен: **{name}**")

    @rotate_status.before_loop
    async def before_rotate(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Status(bot))
