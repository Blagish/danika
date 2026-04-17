from __future__ import annotations

from discord import Embed

from app.systems.dnd5e_wikidot import Dnd5eWikidotSpell

_LEVEL_NAMES = {
    0: "Cantrip",
    1: "1st-level",
    2: "2nd-level",
    3: "3rd-level",
    4: "4th-level",
    5: "5th-level",
    6: "6th-level",
    7: "7th-level",
    8: "8th-level",
    9: "9th-level",
}

_FOOTER_PIC = (
    "https://cdn.discordapp.com/attachments/778998112819085352/964148715067670588/unknown.png"
)


def format_dnd5e_wikidot_spell(spell: Dnd5eWikidotSpell, colour: int) -> Embed:
    """Embed для заклинания D&D 5e (dnd5e.wikidot.com).

    Attributes:
        spell: Данные заклинания.
        colour: Цвет Embed.
    """
    level_str = _LEVEL_NAMES.get(spell.level, f"{spell.level}-й уровень")
    subtitle = f"{level_str} • {spell.school}"
    if spell.ritual:
        subtitle += " (ritual)"

    description = f"""*{subtitle}*
> **Casting Time:** {spell.casting_time}
> **Range:** {spell.range}
> **Components:** {spell.components}
> **Duration:** {spell.duration}
{spell.description}
"""

    embed = Embed(
        title=spell.name,
        description=description,
        url=spell.url,
        colour=colour,
    )
    if spell.higher_levels:
        embed.add_field(name="At Higher Levels", value=spell.higher_levels, inline=False)
    if spell.classes:
        embed.add_field(name="Spell Lists", value=", ".join(spell.classes), inline=False)

    footer = spell.source or "Source: dnd5e.wikidot.com"
    embed.set_footer(text=footer, icon_url=_FOOTER_PIC)
    return embed
