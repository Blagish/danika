from pathlib import Path

from lark import Lark, UnexpectedInput
from lark.exceptions import VisitError

from app.dice.evaluator import DiceEvaluator
from app.dice.types import RollResult

_grammar_path = Path(__file__).parent / "grammar.lark"
_parser = Lark(_grammar_path.read_text(), parser="lalr", start="expr")
_evaluator = DiceEvaluator()


def roll(expression: str) -> RollResult:
    """Parse and evaluate a dice expression. Returns a RollResult."""
    try:
        tree = _parser.parse(expression.strip())
    except UnexpectedInput as e:
        raise ValueError(f"Не понял выражение: `{expression}`") from e

    try:
        result: RollResult = _evaluator.transform(tree)
    except VisitError as e:
        raise e.orig_exc from None

    result.expression = expression.strip()
    return result
