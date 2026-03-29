import random

from lark import Transformer, v_args
from lark.lexer import Token

from app.dice.types import RollResult

MAX_DICE_COUNT = 100
MAX_DICE_SIDES = 10_000


def _roll(count: int, sides: int) -> RollResult:
    if count < 1 or count > MAX_DICE_COUNT:
        raise ValueError(f"Количество кубов должно быть от 1 до {MAX_DICE_COUNT}")
    if sides < 1 or sides > MAX_DICE_SIDES:
        raise ValueError(f"Количество граней должно быть от 1 до {MAX_DICE_SIDES}")
    rolls = [random.randint(1, sides) for _ in range(count)]
    return RollResult(total=sum(rolls), rolls=rolls)


def _roll_pick(sides: int, n: int, take: int, highest: bool) -> RollResult:
    """Roll n dice, keep `take` highest (or lowest). Abstraction for adv/dis and future Nk/Nd notation."""
    if n < 1 or n > MAX_DICE_COUNT:
        raise ValueError(f"Количество кубов должно быть от 1 до {MAX_DICE_COUNT}")
    if sides < 1 or sides > MAX_DICE_SIDES:
        raise ValueError(f"Количество граней должно быть от 1 до {MAX_DICE_SIDES}")
    rolls = [random.randint(1, sides) for _ in range(n)]
    selected = sorted(rolls, reverse=highest)[:take]
    return RollResult(total=sum(selected), rolls=rolls)


@v_args(inline=True)
class DiceEvaluator(Transformer):
    def number(self, n: Token) -> RollResult:
        return RollResult(total=int(n))

    def dice_full(self, count: Token, sides: RollResult) -> RollResult:
        return _roll(int(count), int(sides.total))

    def dice_short(self, sides: RollResult) -> RollResult:
        return _roll(1, int(sides.total))

    def dice_adv(self, sides: RollResult) -> RollResult:
        return _roll_pick(int(sides.total), n=2, take=1, highest=True)

    def dice_dis(self, sides: RollResult) -> RollResult:
        return _roll_pick(int(sides.total), n=2, take=1, highest=False)

    def add(self, a: RollResult, b: RollResult) -> RollResult:
        return a + b

    def sub(self, a: RollResult, b: RollResult) -> RollResult:
        return a - b

    def mul(self, a: RollResult, b: RollResult) -> RollResult:
        return a * b

    def div(self, a: RollResult, b: RollResult) -> RollResult:
        return a / b

    def neg(self, a: RollResult) -> RollResult:
        return -a
