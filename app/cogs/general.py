from __future__ import annotations

from collections.abc import Mapping

import discord
from discord import Locale, app_commands
from discord.ext import commands

from app.i18n import ARG_HELP_COMMAND, CMD_HELP, CMD_PING, HELP_SECTION_ORDER, Section, t


def _cmd_desc(cmd: app_commands.Command | app_commands.Group) -> str:
    """Возвращает описание команды как строку."""
    d = cmd.description
    return d.message if isinstance(d, app_commands.locale_str) else d


def _all_app_commands(
    cog: commands.Cog,
) -> list[app_commands.Command | app_commands.Group]:
    """Возвращает все команды модуля, включая гибридные."""
    result: list[app_commands.Command | app_commands.Group] = list(cog.__cog_app_commands__)
    for prefix_cmd in cog.get_commands():
        if isinstance(prefix_cmd, commands.HybridCommand) and prefix_cmd.app_command:
            result.append(prefix_cmd.app_command)
    return result


def _format_params(params: list[app_commands.Parameter], locale: Locale) -> str:
    """Форматирует список параметров команды как читаемую строку."""
    lines: list[str] = []
    for p in params:
        opt = f" {t('help.optional', locale)}" if not p.required else ""
        if p.choices:
            choices_str = " | ".join(f"`{c.name}`" for c in p.choices)
            lines.append(f"**{p.name}**{opt}: {p.description} — {choices_str}")
        else:
            lines.append(f"**{p.name}**{opt}: {p.description}")
    return "\n".join(lines)


def _build_overview_embed(cogs: Mapping[str, commands.Cog], locale: Locale) -> discord.Embed:
    """Собирает Embed со всеми командами, сгруппированными по модулям.

    Attributes:
        cogs: Словарь модулей бота (bot.cogs).
        locale: Язык пользователя.
    """
    embed = discord.Embed(title=t("help.title", locale), colour=discord.Colour.blurple())

    for section in HELP_SECTION_ORDER:
        cog = cogs.get(section)
        if cog is None:
            continue
        lines: list[str] = []
        for cmd in sorted(_all_app_commands(cog), key=lambda c: c.name):
            if isinstance(cmd, app_commands.Group):
                for sub in sorted(cmd.commands, key=lambda c: c.name):
                    lines.append(f"`/{cmd.name} {sub.name}` — {_cmd_desc(sub)}")
            elif isinstance(cmd, app_commands.Command):
                hint = f" {t('help.roll.hint', locale)}" if cmd.name == "roll" else ""
                lines.append(f"`/{cmd.name}` — {_cmd_desc(cmd)}{hint}")
        if lines:
            embed.add_field(
                name=t(f"help.section.{section}", locale),
                value="\n".join(lines),
                inline=False,
            )

    return embed


def _build_command_embed(
    command: str, cogs: Mapping[str, commands.Cog], locale: Locale
) -> discord.Embed | None:
    """Собирает Embed с описанием конкретной команды.

    Attributes:
        command: Имя команды.
        cogs: Словарь модулей бота.
        locale: Язык пользователя.
    """
    if command == "roll":
        embed = discord.Embed(title=t("help.roll.title", locale), colour=discord.Colour.blurple())
        embed.add_field(
            name=t("help.examples", locale),
            value=t("roll.syntax", locale),
            inline=False,
        )
        return embed

    for cog in cogs.values():
        for cmd in _all_app_commands(cog):
            if cmd.name != command:
                continue

            embed = discord.Embed(title=f"/{command}", colour=discord.Colour.blurple())

            if isinstance(cmd, app_commands.Group):
                for sub in sorted(cmd.commands, key=lambda c: c.name):
                    if not isinstance(sub, app_commands.Command):
                        continue
                    sig = " ".join(
                        f"<{p.name}>" if p.required else f"[{p.name}]" for p in sub.parameters
                    )
                    field_name = (
                        f"`/{command} {sub.name} {sig}`" if sig else f"`/{command} {sub.name}`"
                    )
                    params_str = _format_params(sub.parameters, locale) if sub.parameters else "—"
                    embed.add_field(
                        name=field_name,
                        value=f"{_cmd_desc(sub)}\n{params_str}",
                        inline=False,
                    )
            elif isinstance(cmd, app_commands.Command):
                embed.description = _cmd_desc(cmd)
                if cmd.parameters:
                    embed.add_field(
                        name=t("help.parameters", locale),
                        value=_format_params(cmd.parameters, locale),
                        inline=False,
                    )

            return embed

    return None


class General(commands.Cog, name=Section.GENERAL):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._autocomplete_names: list[str] = []

    async def cog_load(self) -> None:
        self._autocomplete_names = sorted(
            cmd.name for cog in self.bot.cogs.values() for cmd in _all_app_commands(cog)
        )

    @app_commands.command(name="ping", description=CMD_PING)
    async def ping(self, interaction: discord.Interaction) -> None:
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! `{latency}ms`")

    @app_commands.command(name="help", description=CMD_HELP)
    @app_commands.describe(command=ARG_HELP_COMMAND)
    async def help(self, interaction: discord.Interaction, command: str | None = None) -> None:
        if command is not None:
            embed = _build_command_embed(command, self.bot.cogs, interaction.locale)
            if embed is None:
                await interaction.response.send_message(
                    t("help.not_found", interaction.locale), ephemeral=True
                )
                return
        else:
            embed = _build_overview_embed(self.bot.cogs, interaction.locale)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help.autocomplete("command")
    async def help_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=n, value=n)
            for n in self._autocomplete_names
            if current.lower() in n
        ]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
