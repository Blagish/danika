import random

from lark import Transformer, v_args
from lark.lexer import Token

from app.dice.types import RollResult

MAX_DICE_COUNT = 100
MAX_DICE_SIDES = 10_000


def _roll(count: int, sides: int) -> RollResult:
    if count < 1 or count > MAX_DICE_COUNT:
        raise ValueError(f"Количество кубов должно быть от 1 до {MAX_DICE_COUNT}")
    if sides < 2 or sides > MAX_DICE_SIDES:
        raise ValueError(f"Количество граней должно быть от 2 до {MAX_DICE_SIDES}")
    rolls = [random.randint(1, sides) for _ in range(count)]
    return RollResult(total=sum(rolls), rolls=rolls)


@v_args(inline=True)
class DiceEvaluator(Transformer):
    def number(self, n: Token) -> RollResult:
        return RollResult(total=int(n))

    def dice_full(self, count: Token, sides: Token) -> RollResult:
        return _roll(int(count), int(sides))

    def dice_short(self, sides: Token) -> RollResult:
        return _roll(1, int(sides))

    def add(self, a: RollResult, b: RollResult) -> RollResult:
        return a + b

    def sub(self, a: RollResult, b: RollResult) -> RollResult:
        return a - b

    def mul(self, a: RollResult, b: RollResult) -> RollResult:
        return a * b

    def div(self, a: RollResult, b: RollResult) -> RollResult:
        return a // b

    def neg(self, a: RollResult) -> RollResult:
        return -a
