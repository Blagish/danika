import random

from lark import Transformer, v_args
from lark.lexer import Token

from app.dice.types import DiceStep, RollResult

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


def _bold(n: int) -> str:
    return f"[**{n}**]"


def _parens(trace: str) -> str:
    """Wrap in parens if trace has additive ops or leading minus (for use inside * and /)."""
    if " + " in trace or " - " in trace or trace.startswith("-"):
        return f"({trace})"
    return trace


def _adv_trace(rolls: list[int], highest: bool) -> str:
    """Format advantage/disadvantage rolls: winner bold, loser strikethrough."""
    winner, loser = (max(rolls), min(rolls)) if highest else (min(rolls), max(rolls))
    prefix = "a" if highest else "d"
    return f"{prefix}[**{winner}**|~~{loser}~~]"


def _is_ungrouped(r: RollResult) -> bool:
    """True если у r ровно один шаг и expr_trace == str(subtotal) — группа ещё не завёрнута в * или /.
    Такой результат можно "сложить" с соседом: константы и одиночные кубики дописываются к его трейсу."""
    return len(r.dice_steps) == 1 and r.expr_trace == str(r.dice_steps[0].subtotal)


@v_args(inline=True)
class DiceEvaluator(Transformer):
    def number(self, n: Token) -> RollResult:
        s = str(int(n))
        return RollResult(total=int(n), expr_trace=s, dice_count=0)

    def dice_full(self, count: Token, sides: RollResult) -> RollResult:
        n = int(count)
        result = _roll(n, int(sides.total))
        trace = " + ".join(_bold(r) for r in result.rolls)
        if n >= 2:
            return RollResult(
                total=result.total,
                rolls=result.rolls,
                dice_steps=[DiceStep(trace=trace, subtotal=result.total)],
                expr_trace=str(result.total),
                dice_count=n,
            )
        # count=1: ведём себя как dice_short — одиночный куб остаётся инлайн
        return RollResult(
            total=result.total,
            rolls=result.rolls,
            dice_steps=[],
            expr_trace=_bold(result.rolls[0]),
            dice_count=1,
        )

    def dice_short(self, sides: RollResult) -> RollResult:
        result = _roll(1, int(sides.total))
        return RollResult(
            total=result.total,
            rolls=result.rolls,
            dice_steps=[],
            expr_trace=_bold(result.rolls[0]),
            dice_count=1,
        )

    def dice_adv(self, sides: RollResult) -> RollResult:
        result = _roll_pick(int(sides.total), n=2, take=1, highest=True)
        trace = _adv_trace(result.rolls, highest=True)
        return RollResult(
            total=result.total,
            rolls=result.rolls,
            dice_steps=[DiceStep(trace=trace, subtotal=result.total)],
            expr_trace=str(result.total),
            dice_count=2,
        )

    def dice_dis(self, sides: RollResult) -> RollResult:
        result = _roll_pick(int(sides.total), n=2, take=1, highest=False)
        trace = _adv_trace(result.rolls, highest=False)
        return RollResult(
            total=result.total,
            rolls=result.rolls,
            dice_steps=[DiceStep(trace=trace, subtotal=result.total)],
            expr_trace=str(result.total),
            dice_count=2,
        )

    def add(self, a: RollResult, b: RollResult) -> RollResult:
        total = a.total + b.total
        rolls = a.rolls + b.rolls
        count = a.dice_count + b.dice_count

        # Если одна сторона — незавёрнутая группа, а другая не имеет своих шагов
        # (константа или одиночный куб), дописываем её в трейс группы.
        # Это позволяет "3d6+5" и "(3d6+1d8)" формировать одну строку с итогом.
        if _is_ungrouped(a) and not b.dice_steps:
            step = a.dice_steps[0]
            return RollResult(
                total=total,
                rolls=rolls,
                dice_steps=[DiceStep(f"{step.trace} + {b.expr_trace}", total)],
                expr_trace=str(total),
                dice_count=count,
            )
        if _is_ungrouped(b) and not a.dice_steps:
            step = b.dice_steps[0]
            return RollResult(
                total=total,
                rolls=rolls,
                dice_steps=[DiceStep(f"{a.expr_trace} + {step.trace}", total)],
                expr_trace=str(total),
                dice_count=count,
            )

        # В остальных случаях — два независимых набора шагов (два mul-контекста и т.п.)
        return RollResult(
            total=total,
            rolls=rolls,
            dice_steps=a.dice_steps + b.dice_steps,
            expr_trace=f"{a.expr_trace} + {b.expr_trace}",
            dice_count=count,
        )

    def sub(self, a: RollResult, b: RollResult) -> RollResult:
        total = a.total - b.total
        rolls = a.rolls + b.rolls
        count = a.dice_count + b.dice_count

        if _is_ungrouped(a) and not b.dice_steps:
            step = a.dice_steps[0]
            return RollResult(
                total=total,
                rolls=rolls,
                dice_steps=[DiceStep(f"{step.trace} - {b.expr_trace}", total)],
                expr_trace=str(total),
                dice_count=count,
            )

        return RollResult(
            total=total,
            rolls=rolls,
            dice_steps=a.dice_steps + b.dice_steps,
            expr_trace=f"{a.expr_trace} - {b.expr_trace}",
            dice_count=count,
        )

    def mul(self, a: RollResult, b: RollResult) -> RollResult:
        total = a.total * b.total
        # mul всегда использует expr_trace операндов (сабтотал или инлайн-куб),
        # добавляя скобки при необходимости. dice_steps обеих сторон сохраняются.
        a_expr = _parens(a.expr_trace)
        b_expr = _parens(b.expr_trace)
        return RollResult(
            total=total,
            rolls=a.rolls + b.rolls,
            dice_steps=a.dice_steps + b.dice_steps,
            expr_trace=f"{a_expr} * {b_expr}",
            dice_count=a.dice_count + b.dice_count,
        )

    def div(self, a: RollResult, b: RollResult) -> RollResult:
        result = a.total / b.total
        total = int(result) if result == int(result) else round(result, 5)
        a_expr = _parens(a.expr_trace)
        b_expr = _parens(b.expr_trace)
        return RollResult(
            total=total,
            rolls=a.rolls + b.rolls,
            dice_steps=a.dice_steps + b.dice_steps,
            expr_trace=f"{a_expr} / {b_expr}",
            dice_count=a.dice_count + b.dice_count,
        )

    def neg(self, a: RollResult) -> RollResult:
        return RollResult(
            total=-a.total,
            rolls=a.rolls,
            dice_steps=a.dice_steps,
            expr_trace=f"-{a.expr_trace}",
            dice_count=a.dice_count,
        )
