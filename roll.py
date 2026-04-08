"""CLI для бросков кубиков: `uv run roll.py 2d6+3`."""

import re
import sys

from app.dice.parser import roll
from app.formatters.dice import RollResponse


def _strip_markdown(text: str) -> str:
    """Убирает Discord markdown (bold, italic, code) для терминального вывода."""
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = text.replace("`", "")
    return text


def main() -> None:
    if len(sys.argv) < 2:
        print("Использование: uv run roll.py <выражение>")
        print("Пример: uv run roll.py 2d6+3")
        raise SystemExit(1)

    expression = " ".join(sys.argv[1:])
    results = roll(expression)
    response = RollResponse.from_rolls(results, expression)
    print(_strip_markdown(str(response)))


if __name__ == "__main__":
    main()
