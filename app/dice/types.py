from dataclasses import dataclass, field


@dataclass
class DiceStep:
    """Одна группа кубиков, которая получит собственную строку -> в ответе бота."""

    trace: str  # "[**1**] + [**4**] + [**6**] + 5"
    subtotal: int | float  # числовой итог группы (показывается как = N в строке)


@dataclass
class RollResult:
    """
    Результат броска кубиков.

    Attributes:
        total: int | float  # Общий результат броска.
        rolls: list[int]  # Список отдельных бросков кубиков.
        dice_steps: list[DiceStep]  # Группы кубиков с 2+ кубами, каждая получает свою строку "->".
        expr_trace: str  # Арифметическое выражение с подставленными сабтоталами / инлайн-кубами.
        dice_count: int  # Общее количество кубиков в броске.
        expression: str  # Исходное арифметическое выражение.
        errors: list[str]  # Список ошибок, возникших при обработке выражения.
    """

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
    # Ошибки, собранные в процессе парсинга и вычисления.
    # Парсер не крашится — накапливает сюда сообщения для вывода пользователю.
    errors: list[str] = field(default_factory=list)
