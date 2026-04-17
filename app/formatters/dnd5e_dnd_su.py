from __future__ import annotations

from discord import Embed

from app.systems.dnd5e_dnd_su import DndSuSpell

_LEVEL_NAMES = {
    0: "Заговор",
    1: "1-й уровень",
    2: "2-й уровень",
    3: "3-й уровень",
    4: "4-й уровень",
    5: "5-й уровень",
    6: "6-й уровень",
    7: "7-й уровень",
    8: "8-й уровень",
    9: "9-й уровень",
}

_FOOTER_PIC = (
    "https://cdn.discordapp.com/attachments/778998112819085352/964148715067670588/unknown.png"
)


def format_dnd_su_spell(spell: DndSuSpell, colour: int) -> Embed:
    """Embed для заклинания D&D 5e (dnd.su).

    Attributes:
        spell: Данные заклинания.
        colour: Цвет Embed.
    """
    level_str = _LEVEL_NAMES.get(spell.level, f"{spell.level}-й уровень")
    subtitle = f"{level_str} • {spell.school}"
    if spell.ritual:
        subtitle += " (ритуал)"

    title = spell.name
    if spell.name_en:
        title += f" [{spell.name_en}]"

    description = f"""*{subtitle}*
> **Время накладывания:** {spell.casting_time}
> **Дистанция:** {spell.spell_range}
> **Компоненты:** {spell.components}
> **Длительность:** {spell.duration}
{spell.description}
"""

    embed = Embed(
        title=title,
        description=description,
        url=spell.url,
        colour=colour,
    )
    if spell.higher_levels:
        embed.add_field(name="На больших уровнях", value=spell.higher_levels, inline=False)
    if spell.classes:
        embed.add_field(name="Классы", value=", ".join(spell.classes), inline=False)
    if spell.subclasses:
        embed.add_field(name="Подклассы", value=", ".join(spell.subclasses), inline=False)

    embed.set_footer(text="dnd.su", icon_url=_FOOTER_PIC)
    return embed
