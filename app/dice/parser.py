from pathlib import Path

from lark import Lark, UnexpectedInput
from lark.exceptions import VisitError

from app.dice.evaluator import DiceEvaluator
from app.dice.types import RollResult

_grammar_path = Path(__file__).parent / "grammar.lark"
_parser = Lark(_grammar_path.read_text(), parser="lalr", start="expr")
_evaluator = DiceEvaluator()


def roll(expression: str) -> RollResult:
    """Parse and evaluate a dice expression. Returns a RollResult.

    Never raises — ошибки накапливаются в RollResult.errors.
    """
    expr = expression.strip()
    try:
        tree = _parser.parse(expr)
    except UnexpectedInput:
        return RollResult(
            total=0,
            expression=expr,
            errors=[f"Не понял выражение: `{expr}`"],
        )

    try:
        result: RollResult = _evaluator.transform(tree)
    except VisitError as e:
        return RollResult(
            total=0,
            expression=expr,
            errors=[str(e.orig_exc)],
        )

    result.expression = expr
    return result
