from dataclasses import dataclass, field
from enum import Enum

from app.dice import ScalarResult


class Opening(Enum):
    COUNTING = "Считаю"  # Для арифметических операций
    ROLLING = "Кидаю"  # Для бросков


@dataclass
class RollResponse:
    """Форматированный ответ результата броска."""

    opening: Opening
    command: str
    result: str
    comment: str = ""
    line_start: str = "->"
    lines: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_roll(cls, roll: ScalarResult) -> "RollResponse":
        """Создает объект RollResponse из ScalarResult."""
        opening = Opening.ROLLING if roll.dice_count else Opening.COUNTING
        lines = [f"{step.trace} = {step.subtotal}" for step in roll.dice_steps]
        if roll.dice_count:
            lines.append(roll.expr_trace)
        return cls(
            opening=opening,
            command=roll.expression,
            result=str(roll.total),
            lines=lines,
            errors=roll.errors,
        )

    def __str__(self) -> str:
        comment = f" для *{self.comment}*" if self.comment else ""
        command = self.command.replace("*", r"\*")
        return f"{self.opening.value} {command}{comment}{self._steps()}\n> **=** `{self.result}`{self._errors()}"

    def _steps(self) -> str:
        return "".join(f"\n> {self.line_start} {line}" for line in self.lines)

    def _errors(self) -> str:
        return "".join(f"\n-# Ошибка: {e}" for e in self.errors)
