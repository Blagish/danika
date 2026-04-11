from __future__ import annotations

from collections.abc import Callable
from typing import Any

import discord
from discord import Embed
from loguru import logger

from app.formatters.systems import format_service_error
from app.systems.base import SystemClient
from app.systems.types import ServiceUnavailableError, SpellMatch

_log = logger.bind(module=__name__)

_CHOICE_TIMEOUT = 60  # секунды на выбор из кнопок


class _LookupButton(discord.ui.Button["LookupChoiceView"]):
    """Кнопка выбора конкретного элемента из результатов поиска."""

    def __init__(self, name: str, slug: str, row: int, style: discord.ButtonStyle) -> None:
        super().__init__(label=name, style=style, row=row)
        self.slug = slug

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is None or self.view.handled:
            return
        self.view.handled = True
        await interaction.response.defer()

        try:
            result = await self.view.client.fetch_spell(self.slug)
        except ServiceUnavailableError as exc:
            _log.warning(f"Service unavailable: {exc.host}")
            await interaction.edit_original_response(
                embed=format_service_error(exc.host),
                view=None,
            )
            return

        embed = self.view.formatter(result, self.view.client.colour)
        await interaction.edit_original_response(embed=embed, view=None)


class LookupChoiceView(discord.ui.View):
    """Кнопки для выбора элемента из нескольких совпадений.

    Attributes:
        client: Клиент системы для лукапа по slug.
        formatter: Форматтер для итогового эмбеда.
    """

    def __init__(
        self,
        choices: list[SpellMatch],
        client: SystemClient[Any],
        formatter: Callable[[Any, int], Embed],
        button_style: discord.ButtonStyle = discord.ButtonStyle.secondary,
    ) -> None:
        super().__init__(timeout=_CHOICE_TIMEOUT)
        self.client = client
        self.formatter = formatter
        self.handled: bool = False

        for i, choice in enumerate(choices[:25]):
            self.add_item(_LookupButton(choice.name, choice.slug, row=i // 5, style=button_style))
