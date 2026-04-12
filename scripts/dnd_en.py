"""CLI для поиска заклинаний D&D 5e (EN): `uv run scripts/dnd_en.py fireball`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from typing import cast

import click

from app.formatters.dnd5e_wikidot import format_dnd5e_wikidot_spell
from app.systems.dnd5e_wikidot import Dnd5eWikidotClient, Dnd5eWikidotSpell, Dnd2024WikidotClient
from app.systems.types import ServiceUnavailableError, SpellMatch
from scripts._utils import render_embed, strip_markdown


@click.command()
@click.argument("name", nargs=-1, required=True)
@click.option("--edition", type=click.Choice(["2014", "2024"]), default="2014", show_default=True)
def main(name: tuple[str, ...], edition: str) -> None:
    """Look up a D&D 5e spell in English (source: dnd5e.wikidot.com)."""
    asyncio.run(_lookup(" ".join(name), edition))


async def _lookup(name: str, edition: str) -> None:
    client = Dnd2024WikidotClient() if edition == "2024" else Dnd5eWikidotClient()
    try:
        result: Dnd5eWikidotSpell | list[SpellMatch] | None = await client.search_spell(name)
    except ServiceUnavailableError as e:
        raise click.ClickException(str(e)) from e
    finally:
        await client.close()

    if result is None:
        raise click.ClickException(f"Spell not found: {name!r}")

    if isinstance(result, list):
        click.echo(f"Multiple results for {name!r}:")
        for match in cast(list[SpellMatch], result):
            click.echo(f"  - {match.name}")
        return

    embed = format_dnd5e_wikidot_spell(result, 0)
    click.echo(strip_markdown(render_embed(embed)))


if __name__ == "__main__":
    main()
