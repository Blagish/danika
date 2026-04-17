from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import discord
from discord import Embed, app_commands
from discord.ext import commands, tasks
from loguru import logger

from app.formatters.dnd5e_dnd_su import format_dnd_su_spell
from app.formatters.dnd5e_wikidot import format_dnd5e_wikidot_spell
from app.formatters.systems import (
    format_not_found,
    format_service_error,
    format_spell_choices,
    format_too_short,
)
from app.i18n import (
    ARG_EDITION,
    ARG_PF2_SPELL_NAME,
    ARG_SOURCE_LANG,
    ARG_SPELL_NAME,
    CMD_DND_SPELL,
    CMD_PF2_SPELL,
    Section,
)
from app.systems.base import SystemClient
from app.systems.dnd5e_dnd_su import DndSu2024Client, DndSuClient
from app.systems.dnd5e_wikidot import Dnd5eWikidotClient, Dnd2024WikidotClient
from app.systems.types import ServiceUnavailableError, SpellMatch
from app.views import LookupChoiceView

_log = logger.bind(module=__name__)

MIN_QUERY_LENGTH = 3


class Systems(commands.Cog, name=Section.LOOKUP):
    """Команды поиска по игровым системам."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.dnd_en: Dnd5eWikidotClient = Dnd5eWikidotClient()
        self.dnd_en24: Dnd2024WikidotClient = Dnd2024WikidotClient()
        self.dnd_ru: DndSuClient = DndSuClient()
        self.dnd_ru24: DndSu2024Client = DndSu2024Client()
        self.pf2: SystemClient[Any] | None = None

    async def cog_load(self) -> None:
        self._refresh_spell_lists.start()

    async def cog_unload(self) -> None:
        self._refresh_spell_lists.cancel()
        for client in (self.dnd_en, self.dnd_en24, self.dnd_ru, self.dnd_ru24, self.pf2):
            if client:
                await client.close()

    @tasks.loop(hours=24)
    async def _refresh_spell_lists(self) -> None:
        """Обновляет списки заклинаний для всех клиентов. Первый вызов — предзагрузка при старте."""
        clients = [self.dnd_en, self.dnd_en24, self.dnd_ru, self.dnd_ru24]
        results = await asyncio.gather(*[c.reload() for c in clients], return_exceptions=True)
        for client, result in zip(clients, results, strict=True):
            if isinstance(result, Exception):
                _log.warning(f"{client.system_name}: ошибка обновления списка: {result}")

    @_refresh_spell_lists.before_loop
    async def _before_refresh_spell_lists(self) -> None:
        await self.bot.wait_until_ready()

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
            formatter: Функция для форматирования результата в Embed.
        """
        if client is None:
            await interaction.followup.send("Этот источник ещё не подключён.")
            return

        if len(name.strip()) < MIN_QUERY_LENGTH:
            await interaction.followup.send(embed=format_too_short())
            return

        with logger.contextualize(user=interaction.user.id, query=name):
            try:
                result = await client.search_spell(name)
            except ServiceUnavailableError as exc:
                _log.warning(f"Service unavailable: {exc.host}")
                await interaction.followup.send(embed=format_service_error(exc.host))
                return

            match result:
                case list() as choices if all(isinstance(c, SpellMatch) for c in choices):
                    view = LookupChoiceView(choices, client, formatter)
                    await interaction.followup.send(
                        embed=format_spell_choices(choices),
                        view=view,
                    )
                    return
                case None:
                    embed = format_not_found(name)
                case spell:
                    embed = formatter(spell, client.colour)

            await interaction.followup.send(embed=embed)

    # -- D&D 5e ---------------------------------------------------------------

    dnd = app_commands.Group(name="dnd", description="D&D 5e")

    @dnd.command(name="spell", description=CMD_DND_SPELL)
    @app_commands.describe(
        name=ARG_SPELL_NAME,
        lang=ARG_SOURCE_LANG,
        edition=ARG_EDITION,
    )
    @app_commands.choices(
        lang=[
            app_commands.Choice(name="English", value="en"),
            app_commands.Choice(name="Русский", value="ru"),
        ],
        edition=[
            app_commands.Choice(name="D&D 5e", value="5e"),
            app_commands.Choice(name="D&D 5.5e (2024)", value="5.5e"),
        ],
    )
    async def dnd_spell(
        self,
        interaction: discord.Interaction,
        name: str,
        lang: app_commands.Choice[str] | None = None,
        edition: app_commands.Choice[str] | None = None,
    ) -> None:
        await interaction.response.defer()
        is_ru = (lang.value if lang else "en") == "ru"
        is_2024 = (edition.value if edition else "5e") == "5.5e"

        if is_ru:
            client = self.dnd_ru24 if is_2024 else self.dnd_ru
            await self._do_spell_lookup(interaction, client, name, format_dnd_su_spell)
        else:
            translator = self.dnd_ru24 if is_2024 else self.dnd_ru
            en_name = await translator.translate_to_en(name) or name
            client = self.dnd_en24 if is_2024 else self.dnd_en
            await self._do_spell_lookup(interaction, client, en_name, format_dnd5e_wikidot_spell)

    # -- Pathfinder 2e --------------------------------------------------------

    pf2_group = app_commands.Group(name="pf2", description="Pathfinder 2e")

    @pf2_group.command(name="spell", description=CMD_PF2_SPELL)
    @app_commands.describe(name=ARG_PF2_SPELL_NAME)
    async def pf2_spell(self, interaction: discord.Interaction, name: str) -> None:
        await interaction.response.defer()
        await interaction.followup.send("PF2 spell lookup ещё не реализован.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Systems(bot))
