from dataclasses import dataclass, field


@dataclass
class DiceStep:
    """Одна группа кубиков, которая получит собственную строку -> в ответе бота."""

    trace: str  # "[**1**] + [**4**] + [**6**] + 5"
    subtotal: int | float  # числовой итог группы (показывается как = N в строке)


@dataclass
class RollValue:
    """Базовый класс результата вычисления: общие поля для скаляра и массива.

    Attributes:
        total: Числовой итог выражения.
        rolls: Плоский список всех отдельных бросков кубиков.
        dice_steps: Группы с 2+ кубами — каждая получает строку «->» в ответе.
            Одиночный куб и константы остаются инлайн в expr_trace.
        expr_trace: Арифметическое выражение с подставленными сабтоталами / инлайн-кубами.
            Используется форматтером как строка «-> {expr_trace}».
        dice_count: Суммарное число кубиков в выражении.
            Форматтер показывает строку «->» только если dice_count >= 1.
        expression: Исходное выражение, введённое пользователем.
        errors: Ошибки парсинга и вычисления. Парсер не крашится — накапливает сюда.
    """

    total: int | float
    rolls: list[int] = field(default_factory=list)
    dice_steps: list[DiceStep] = field(default_factory=list)
    expr_trace: str = ""
    dice_count: int = 0
    expression: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def is_ungrouped(self) -> bool:
        """True если результат — незавёрнутая группа: ровно один шаг и expr_trace == str(subtotal).
        Такой результат можно "сложить" с соседом: константы и одиночные кубики дописываются к его трейсу."""
        return len(self.dice_steps) == 1 and self.expr_trace == str(
            self.dice_steps[0].subtotal
        )


@dataclass
class ScalarResult(RollValue):
    """Одно числовое значение — результат броска, арифметики или константы.

    Новых атрибутов не добавляет — наследует всё от RollValue.
    Существует как отдельный тип для различения от ArrayResult в isinstance-проверках.
    """


@dataclass
class ArrayResult(RollValue):
    """Список скалярных результатов — от repeat/map. В арифметике ведёт себя как сумма items.

    Attributes:
        items: Элементы массива — отдельные ScalarResult от каждой итерации.
    """

    items: list[ScalarResult] = field(default_factory=list)
