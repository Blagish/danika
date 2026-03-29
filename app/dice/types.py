from dataclasses import dataclass, field


@dataclass
class RollResult:
    total: int | float
    rolls: list[int] = field(default_factory=list)
    expression: str = ""

    def __add__(self, other: "RollResult") -> "RollResult":
        return RollResult(
            total=self.total + other.total,
            rolls=self.rolls + other.rolls,
        )

    def __sub__(self, other: "RollResult") -> "RollResult":
        return RollResult(
            total=self.total - other.total,
            rolls=self.rolls + other.rolls,
        )

    def __mul__(self, other: "RollResult") -> "RollResult":
        return RollResult(
            total=self.total * other.total,
            rolls=self.rolls + other.rolls,
        )

    def __truediv__(self, other: "RollResult") -> "RollResult":
        result = self.total / other.total
        total = int(result) if result == int(result) else round(result, 5)
        return RollResult(total=total, rolls=self.rolls + other.rolls)

    def __neg__(self) -> "RollResult":
        return RollResult(total=-self.total, rolls=self.rolls)
