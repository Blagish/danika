from dataclasses import dataclass, field
from enum import Enum

from app.dice.types import ScalarResult


class Opening(Enum):
    COUNTING = "Считаю"  # Для арифметических операций
    ROLLING = "Кидаю"  # Для бросков


@dataclass
class RollResponse:
    """Форматированный ответ результата броска (одного или нескольких через запятую)."""

    opening: Opening
    command: str
    result: str
    comment: str = ""
    line_start: str = "->"
    lines: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_rolls(cls, rolls: list[ScalarResult], expression: str) -> RollResponse:
        """Создаёт один блок ответа из списка результатов.

        Промежуточные шаги каждого выражения идут на отдельных строках.
        Финальные строки `->` всех выражений объединяются через запятую.

        Attributes:
            rolls: Результаты вычисления каждого выражения.
            expression: Исходное выражение, введённое пользователем.
        """
        opening = Opening.ROLLING if any(r.dice_count for r in rolls) else Opening.COUNTING

        intermediate_lines: list[str] = []
        final_parts: list[str] = []

        for roll in rolls:
            if roll.is_ungrouped:
                per_roll_lines = [roll.dice_steps[0].trace]
            else:
                per_roll_lines = [f"{step.trace} = {step.subtotal}" for step in roll.dice_steps]
                if roll.dice_count:
                    per_roll_lines.append(roll.expr_trace)

            if per_roll_lines:
                intermediate_lines.extend(per_roll_lines[:-1])
                final_parts.append(per_roll_lines[-1])

        all_lines = intermediate_lines
        if final_parts:
            all_lines.append(", ".join(final_parts))

        result = ", ".join(str(r.total) for r in rolls)
        errors = [e for r in rolls for e in r.errors]

        return cls(
            opening=opening,
            command=expression,
            result=result,
            lines=all_lines,
            errors=errors,
        )

    def __str__(self) -> str:
        comment = f" для *{self.comment}*" if self.comment else ""
        command = self.command.replace("*", r"\*")
        steps = self._steps()
        errors = self._errors()
        return f"{self.opening.value} {command}{comment}{steps}\n> **=** `{self.result}`{errors}"

    def _steps(self) -> str:
        return "".join(f"\n> {self.line_start} {line}" for line in self.lines)

    def _errors(self) -> str:
        return "".join(f"\n-# Ошибка: {e}" for e in self.errors)
