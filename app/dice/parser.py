from pathlib import Path

from lark import Lark, UnexpectedInput
from lark.exceptions import VisitError

from app.dice.evaluator import DiceEvaluator
from app.dice.types import ScalarResult

_grammar_path = Path(__file__).parent / "grammar.lark"
_parser = Lark(_grammar_path.read_text(), parser="lalr", start="start")
_evaluator = DiceEvaluator()


def roll(expression: str) -> list[ScalarResult]:
    """Парсит и вычисляет выражение с броском кубиков. Возвращает список результатов.

    Для одного выражения список из одного элемента. Ошибки хранятся в ScalarResult.errors."""
    expr = expression.strip()
    # TODO: ручной split дублирует грамматику и сломается на запятых внутри скобок.
    #  Подумать — нужен ли per-result expression вообще, раз форматтер берёт полную строку.
    sub_exprs = [e.strip() for e in expr.split(",")]
    try:
        tree = _parser.parse(expr)
    except UnexpectedInput:
        return [
            ScalarResult(
                total=0,
                expression=expr,
                errors=[f"Не распознала выражение: `{expr}`"],
            )
        ]

    try:
        results: list[ScalarResult] = _evaluator.transform(tree)
    except VisitError as e:
        return [
            ScalarResult(
                total=0,
                expression=expr,
                errors=[str(e.orig_exc)],
            )
        ]

    for result, sub_expr in zip(results, sub_exprs, strict=False):
        result.expression = sub_expr
    return results
