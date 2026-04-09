from __future__ import annotations

from collections.abc import Callable
from typing import Any

import discord
from discord import Embed, app_commands
from discord.ext import commands
from loguru import logger

from app.formatters.dnd5e_wikidot import format_dnd5e_wikidot_spell
from app.formatters.systems import (
    format_not_found,
    format_service_error,
    format_spell_choices,
    format_too_short,
)
from app.systems.base import SystemClient
from app.systems.dnd5e_wikidot import Dnd5eWikidotClient
from app.systems.types import ServiceUnavailableError, SpellMatch

MIN_QUERY_LENGTH = 3


class Systems(commands.Cog):
    """Команды поиска по игровым системам."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.dnd_en: Dnd5eWikidotClient = Dnd5eWikidotClient()
        self.dnd_ru: SystemClient[Any] | None = None
        self.pf2: SystemClient[Any] | None = None

    async def cog_unload(self) -> None:
        for client in (self.dnd_en, self.dnd_ru, self.pf2):
            if client:
                await client.close()

    # -- shared logic ---------------------------------------------------------

    async def _do_spell_lookup(
        self,
        interaction: discord.Interaction,
        client: SystemClient[Any] | None,
        name: str,
        formatter: Callable[[Any, int], Embed],
    ) -> None:
        """Поиск заклинания через *client* и отправка результата.

        Attributes:
            interaction: Текущее взаимодействие Discord.
            client: Клиент игровой системы.
            name: Поисковый запрос.
            formatter: Функция, превращающая данные заклинания в эмбед.
        """
        if client is None:
            await interaction.followup.send("Этот источник ещё не подключён.")
            return

        if len(name.strip()) < MIN_QUERY_LENGTH:
            await interaction.followup.send(embed=format_too_short())
            return

        try:
            result = await client.search_spell(name)
        except ServiceUnavailableError as exc:
            logger.warning(f"Service unavailable: {exc.host}")
            await interaction.followup.send(embed=format_service_error(exc.host))
            return

        match result:
            case list() as choices if all(isinstance(c, SpellMatch) for c in choices):
                embed = format_spell_choices(choices)
            case None:
                embed = format_not_found(name)
            case spell:
                embed = formatter(spell, client.colour)

        await interaction.followup.send(embed=embed)

    # -- D&D 5e ---------------------------------------------------------------

    dnd = app_commands.Group(name="dnd", description="D&D 5e")

    @dnd.command(name="spell", description="Найти заклинание D&D 5e")
    @app_commands.describe(
        name="Название заклинания",
        lang="Язык источника",
    )
    @app_commands.choices(
        lang=[
            app_commands.Choice(name="English", value="en"),
            app_commands.Choice(name="Русский", value="ru"),
        ]
    )
    async def dnd_spell(
        self,
        interaction: discord.Interaction,
        name: str,
        lang: app_commands.Choice[str] | None = None,
    ) -> None:
        await interaction.response.defer()
        language = lang.value if lang else "en"
        client: SystemClient[Any] | None = self.dnd_ru if language == "ru" else self.dnd_en
        await self._do_spell_lookup(interaction, client, name, format_dnd5e_wikidot_spell)

    # -- Pathfinder 2e --------------------------------------------------------

    pf2_group = app_commands.Group(name="pf2", description="Pathfinder 2e")

    @pf2_group.command(name="spell", description="Найти заклинание Pathfinder 2e")
    @app_commands.describe(name="Название заклинания (на английском)")
    async def pf2_spell(self, interaction: discord.Interaction, name: str) -> None:
        await interaction.response.defer()
        await interaction.followup.send("PF2 spell lookup ещё не реализован.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Systems(bot))
