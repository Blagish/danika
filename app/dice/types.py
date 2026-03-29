from dataclasses import dataclass, field


@dataclass
class DiceStep:
    """Одна группа кубиков, которая получит собственную строку -> в ответе бота."""

    trace: str  # "[**1**] + [**4**] + [**6**] + 5"
    subtotal: int | float  # числовой итог группы (показывается как = N в строке)


@dataclass
class RollResult:
    total: int | float
    rolls: list[int] = field(default_factory=list)
    # Группы с 2+ кубами: каждая получит свою строку "->".
    # Одиночный куб и чистые числа — не создают шаги, остаются инлайн в expr_trace.
    dice_steps: list[DiceStep] = field(default_factory=list)
    # Арифметическое выражение с подставленными сабтоталами / инлайн-кубами.
    # Используется форматтером как строка "-> {expr_trace}".
    expr_trace: str = ""
    # Суммарное число кубиков в субвыражении.
    # Форматтер показывает строку "->" только если dice_count >= 1.
    dice_count: int = 0
    expression: str = ""
