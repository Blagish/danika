"""CLI для поиска заклинаний D&D 5e (RU): `uv run scripts/dnd_ru.py огненный шар`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from typing import cast

import click

from app.formatters.dnd5e_dnd_su import format_dnd_su_spell
from app.systems.dnd5e_dnd_su import DndSu2024Client, DndSuClient, DndSuSpell
from app.systems.types import ServiceUnavailableError, SpellMatch
from scripts._utils import render_embed, strip_markdown


@click.command()
@click.argument("name", nargs=-1, required=True)
@click.option("--edition", type=click.Choice(["2014", "2024"]), default="2014", show_default=True)
def main(name: tuple[str, ...], edition: str) -> None:
    """Найти заклинание D&D 5e на русском (источник: dnd.su)."""
    asyncio.run(_lookup(" ".join(name), edition))


async def _lookup(name: str, edition: str) -> None:
    client = DndSu2024Client() if edition == "2024" else DndSuClient()
    try:
        result: DndSuSpell | list[SpellMatch] | None = await client.search_spell(name)
    except ServiceUnavailableError as e:
        raise click.ClickException(str(e)) from e
    finally:
        await client.close()

    if result is None:
        raise click.ClickException(f"Заклинание не найдено: {name!r}")

    if isinstance(result, list):
        click.echo(f"Несколько результатов для {name!r}:")
        for match in cast(list[SpellMatch], result):
            click.echo(f"  - {match.name}")
        return

    embed = format_dnd_su_spell(result, 0)
    click.echo(strip_markdown(render_embed(embed)))


if __name__ == "__main__":
    main()
