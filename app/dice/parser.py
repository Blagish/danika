from pathlib import Path

from lark import Lark, UnexpectedInput
from lark.exceptions import VisitError

from app.dice.evaluator import DiceEvaluator
from app.dice.types import ScalarResult

_grammar_path = Path(__file__).parent / "grammar.lark"
_parser = Lark(_grammar_path.read_text(), parser="lalr", start="expr")
_evaluator = DiceEvaluator()


def roll(expression: str) -> ScalarResult:
    """Парсит и вычисляет выражение с броском кубиков. Возвращает ScalarResult.

    Ошибки хранятся в ScalarResult.errors."""
    expr = expression.strip()
    try:
        tree = _parser.parse(expr)
    except UnexpectedInput:
        return ScalarResult(
            total=0,
            expression=expr,
            errors=[f"Не распознала выражение: `{expr}`"],
        )

    try:
        result: ScalarResult = _evaluator.transform(tree)
    except VisitError as e:
        return ScalarResult(
            total=0,
            expression=expr,
            errors=[str(e.orig_exc)],
        )

    result.expression = expr
    return result
