"""CLI для бросков кубиков: `uv run scripts/roll.py 2d6+3`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import click

from app.dice.parser import roll
from app.formatters.dice import RollResponse
from scripts._utils import strip_markdown


@click.command()
@click.argument("expression", nargs=-1, required=True)
def main(expression: tuple[str, ...]) -> None:
    """Бросить кубики по выражению.

    Примеры: 2d6+3, d20+5, 4d6p3, 2d6+3, 3d8
    """
    expr = " ".join(expression)
    results = roll(expr)
    response = RollResponse.from_rolls(results, expr)
    click.echo(strip_markdown(str(response)))


if __name__ == "__main__":
    main()
