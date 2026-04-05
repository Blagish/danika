import random

from lark import Transformer, v_args
from lark.lexer import Token
from app.dice.types import DiceStep, ScalarResult
from app.dice.trace import _bold, _parens, _pick_trace, _adv_trace

MAX_DICE_COUNT = 100
MAX_DICE_SIDES = 10_000


def _validate_dice(count: int, sides: int) -> list[str]:
    errors = []
    if count < 1 or count > MAX_DICE_COUNT:
        errors.append(f"Количество кубов должно быть от 1 до {MAX_DICE_COUNT}")
    if sides < 1 or sides > MAX_DICE_SIDES:
        errors.append(f"Количество граней должно быть от 1 до {MAX_DICE_SIDES}")
    return errors


def _roll(count: int, sides: int) -> ScalarResult:
    if errors := _validate_dice(count, sides):
        return ScalarResult(total=0, errors=errors)
    rolls = [random.randint(1, sides) for _ in range(count)]
    return ScalarResult(total=sum(rolls), rolls=rolls)


def _roll_pick(sides: int, n: int, take: int, highest: bool) -> ScalarResult:
    """Кидает n кубов и оставляет `take` самых высоких (или низких) бросков. Абстракция для преимущества/помехи и будущих Nk/Nd нотаций."""
    if errors := _validate_dice(n, sides):
        return ScalarResult(total=0, errors=errors)
    rolls = [random.randint(1, sides) for _ in range(n)]
    selected = sorted(rolls, reverse=highest)[:take]
    return ScalarResult(total=sum(selected), rolls=rolls)


def _bin_combine(
    a: ScalarResult, b: ScalarResult
) -> tuple[list[int], list[DiceStep], list[str], int]:
    """Объединяет поля двух операндов для бинарной операции: (rolls, steps, errors, dice_count)."""
    return (
        a.rolls + b.rolls,
        a.dice_steps + b.dice_steps,
        a.errors + b.errors,
        a.dice_count + b.dice_count,
    )


@v_args(inline=True)
class DiceEvaluator(Transformer):
    def number(self, n: Token) -> ScalarResult:
        s = str(int(n))
        return ScalarResult(total=int(n), expr_trace=s, dice_count=0)

    def dice_pick(
        self, count: ScalarResult, sides: ScalarResult, take: Token
    ) -> ScalarResult:
        n = int(count.total)
        t = int(take)
        errors = count.errors + sides.errors
        if t < 1 or t >= n:
            errors.append(f"p должно быть от 1 до {n - 1} (бросается {n} кубов)")
            return ScalarResult(total=0, expr_trace="0", errors=errors)
        result = _roll_pick(int(sides.total), n=n, take=t, highest=True)
        errors.extend(result.errors)
        if errors:
            return ScalarResult(total=0, expr_trace="0", errors=errors)
        trace = _pick_trace(result.rolls, t, highest=True)
        return ScalarResult(
            total=result.total,
            rolls=result.rolls,
            dice_steps=[DiceStep(trace=trace, subtotal=result.total)],
            expr_trace=str(result.total),
            dice_count=n,
        )

    def dice_full(self, count: ScalarResult, sides: ScalarResult) -> ScalarResult:
        n = int(count.total)
        errors = count.errors + sides.errors
        result = _roll(n, int(sides.total))
        errors.extend(result.errors)
        if errors:
            return ScalarResult(total=0, expr_trace="0", errors=errors)
        if n == 1:
            return ScalarResult(
                total=result.total,
                rolls=result.rolls,
                dice_steps=[],
                expr_trace=_bold(result.rolls[0]),
                dice_count=1,
            )
        trace = " + ".join(_bold(r) for r in result.rolls)
        return ScalarResult(
            total=result.total,
            rolls=result.rolls,
            dice_steps=[DiceStep(trace=trace, subtotal=result.total)],
            expr_trace=str(result.total),
            dice_count=n,
        )

    def dice_short(self, sides: ScalarResult) -> ScalarResult:
        errors = sides.errors[:]
        result = _roll(1, int(sides.total))
        errors.extend(result.errors)
        if errors:
            return ScalarResult(total=0, expr_trace="0", errors=errors)
        return ScalarResult(
            total=result.total,
            rolls=result.rolls,
            dice_steps=[],
            expr_trace=_bold(result.rolls[0]),
            dice_count=1,
        )

    def _dice_adv_dis(self, sides: ScalarResult, highest: bool) -> ScalarResult:
        errors = sides.errors[:]
        result = _roll_pick(int(sides.total), n=2, take=1, highest=highest)
        errors.extend(result.errors)
        if errors:
            return ScalarResult(total=0, expr_trace="0", errors=errors)
        trace = _adv_trace(result.rolls, highest=highest)
        return ScalarResult(
            total=result.total,
            rolls=result.rolls,
            dice_steps=[DiceStep(trace=trace, subtotal=result.total)],
            expr_trace=str(result.total),
            dice_count=2,
        )

    def dice_adv(self, sides: ScalarResult) -> ScalarResult:
        return self._dice_adv_dis(sides, highest=True)

    def dice_dis(self, sides: ScalarResult) -> ScalarResult:
        return self._dice_adv_dis(sides, highest=False)

    def add(self, a: ScalarResult, b: ScalarResult) -> ScalarResult:
        rolls, steps, errors, count = _bin_combine(a, b)
        total = a.total + b.total
        # Если одна сторона — незавёрнутая группа, а другая не имеет своих шагов
        # (константа или одиночный куб), дописываем её в трейс группы.
        # Это позволяет "3d6+5" и "(3d6+1d8)" формировать одну строку с итогом.
        if a.is_ungrouped and not b.dice_steps:
            return ScalarResult(
                total=total,
                rolls=rolls,
                dice_steps=[
                    DiceStep(f"{a.dice_steps[0].trace} + {b.expr_trace}", total)
                ],
                expr_trace=str(total),
                dice_count=count,
                errors=errors,
            )
        if b.is_ungrouped and not a.dice_steps:
            return ScalarResult(
                total=total,
                rolls=rolls,
                dice_steps=[
                    DiceStep(f"{a.expr_trace} + {b.dice_steps[0].trace}", total)
                ],
                expr_trace=str(total),
                dice_count=count,
                errors=errors,
            )
        return ScalarResult(
            total=total,
            rolls=rolls,
            dice_steps=steps,
            expr_trace=f"{a.expr_trace} + {b.expr_trace}",
            dice_count=count,
            errors=errors,
        )

    def sub(self, a: ScalarResult, b: ScalarResult) -> ScalarResult:
        rolls, steps, errors, count = _bin_combine(a, b)
        total = a.total - b.total
        if a.is_ungrouped and not b.dice_steps:
            return ScalarResult(
                total=total,
                rolls=rolls,
                dice_steps=[
                    DiceStep(f"{a.dice_steps[0].trace} - {b.expr_trace}", total)
                ],
                expr_trace=str(total),
                dice_count=count,
                errors=errors,
            )
        return ScalarResult(
            total=total,
            rolls=rolls,
            dice_steps=steps,
            expr_trace=f"{a.expr_trace} - {b.expr_trace}",
            dice_count=count,
            errors=errors,
        )

    def mul(self, a: ScalarResult, b: ScalarResult) -> ScalarResult:
        rolls, steps, errors, count = _bin_combine(a, b)
        # mul всегда использует expr_trace операндов (сабтотал или инлайн-куб),
        # добавляя скобки при необходимости. dice_steps обеих сторон сохраняются.
        return ScalarResult(
            total=a.total * b.total,
            rolls=rolls,
            dice_steps=steps,
            expr_trace=f"{_parens(a.expr_trace)} * {_parens(b.expr_trace)}",
            dice_count=count,
            errors=errors,
        )

    def div(self, a: ScalarResult, b: ScalarResult) -> ScalarResult:
        rolls, steps, errors, count = _bin_combine(a, b)
        expr_trace = f"{_parens(a.expr_trace)} / {_parens(b.expr_trace)}"
        if b.total == 0:
            errors.append("Деление на ноль")
            return ScalarResult(
                total=0,
                rolls=rolls,
                dice_steps=steps,
                expr_trace=expr_trace,
                dice_count=count,
                errors=errors,
            )
        result = a.total / b.total
        total = int(result) if result == int(result) else round(result, 5)
        return ScalarResult(
            total=total,
            rolls=rolls,
            dice_steps=steps,
            expr_trace=expr_trace,
            dice_count=count,
            errors=errors,
        )

    def truediv(self, a: ScalarResult, b: ScalarResult) -> ScalarResult:
        rolls, steps, errors, count = _bin_combine(a, b)
        expr_trace = f"{_parens(a.expr_trace)} // {_parens(b.expr_trace)}"
        if b.total == 0:
            errors.append("Деление на ноль")
            return ScalarResult(
                total=0,
                rolls=rolls,
                dice_steps=steps,
                expr_trace=expr_trace,
                dice_count=count,
                errors=errors,
            )
        return ScalarResult(
            total=a.total // b.total,
            rolls=rolls,
            dice_steps=steps,
            expr_trace=expr_trace,
            dice_count=count,
            errors=errors,
        )

    def start(self, *items: ScalarResult) -> list[ScalarResult]:
        return list(items)

    def neg(self, a: ScalarResult) -> ScalarResult:
        inner = a.expr_trace
        if inner.startswith("-") and " + " not in inner and " - " not in inner:
            new_trace = inner[1:]
        elif " + " in inner or " - " in inner:
            new_trace = f"-({inner})"
        else:
            new_trace = f"-{inner}"
        return ScalarResult(
            total=-a.total,
            rolls=a.rolls,
            dice_steps=a.dice_steps,
            expr_trace=new_trace,
            dice_count=a.dice_count,
            errors=a.errors,
        )
