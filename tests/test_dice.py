import pytest

from app.dice import roll
from app.dice.types import ScalarResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assert_result(r: ScalarResult, *, total=None, dice_count=None, num_rolls=None):
    if total is not None:
        assert r.total == total
    if dice_count is not None:
        assert r.dice_count == dice_count
    if num_rolls is not None:
        assert len(r.rolls) == num_rolls


# ---------------------------------------------------------------------------
# Базовые кубы
# ---------------------------------------------------------------------------

class TestBasicDice:
    def test_d20_range(self):
        for _ in range(50):
            r = roll("d20")
            assert 1 <= r.total <= 20

    def test_d20_cyrillic(self):
        r = roll("д20")
        assert 1 <= r.total <= 20

    def test_ndice_count(self):
        r = roll("3d6")
        assert len(r.rolls) == 3
        assert all(1 <= x <= 6 for x in r.rolls)
        assert r.total == sum(r.rolls)

    def test_ndice_range(self):
        for _ in range(50):
            r = roll("4d10")
            assert 4 <= r.total <= 40

    def test_d_expr_sides(self):
        """d(15+5) должно быть идентично d20."""
        for _ in range(50):
            r = roll("d(15+5)")
            assert 1 <= r.total <= 20

    def test_d_expr_nested(self):
        """d(d4+16): стороны от 17 до 20."""
        for _ in range(50):
            r = roll("d(d4+16)")
            assert 1 <= r.total <= 20


# ---------------------------------------------------------------------------
# Арифметика
# ---------------------------------------------------------------------------

class TestArithmetic:
    def test_addition_modifier(self):
        for _ in range(30):
            r = roll("d6+10")
            assert 11 <= r.total <= 16

    def test_subtraction_modifier(self):
        for _ in range(30):
            r = roll("d6-1")
            assert 0 <= r.total <= 5

    def test_multiplication(self):
        r = roll("3*4")
        assert r.total == 12

    def test_true_division(self):
        r = roll("7/2")
        assert r.total == 3.5

    def test_integer_division_stays_int(self):
        r = roll("6/2")
        assert r.total == 3
        assert isinstance(r.total, int)

    def test_operator_precedence(self):
        r = roll("10+3*2")
        assert r.total == 16

    def test_grouping(self):
        r = roll("(10+3)*2")
        assert r.total == 26

    def test_unary_negative(self):
        r = roll("-d6")
        assert -6 <= r.total <= -1

    def test_dice_in_expression(self):
        for _ in range(30):
            r = roll("2*(d6+1)")
            assert 4 <= r.total <= 14


# ---------------------------------------------------------------------------
# Преимущество / Помеха
# ---------------------------------------------------------------------------

class TestAdvantageDisadvantage:
    def test_advantage_picks_highest(self, monkeypatch):
        rolls_iter = iter([3, 17])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(rolls_iter))
        r = roll("ad20")
        assert r.total == 17
        assert r.rolls == [3, 17]

    def test_disadvantage_picks_lowest(self, monkeypatch):
        rolls_iter = iter([3, 17])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(rolls_iter))
        r = roll("dd20")
        assert r.total == 3
        assert r.rolls == [3, 17]

    def test_advantage_cyrillic_a(self):
        for _ in range(30):
            r = roll("аd20")
            assert 1 <= r.total <= 20

    def test_advantage_dice_count(self):
        r = roll("ad20")
        assert r.dice_count == 2
        assert len(r.rolls) == 2

    def test_advantage_not_parsed_as_d_of_d(self):
        """dd20 — помеха, а не d(d20)."""
        for _ in range(30):
            r = roll("dd20")
            assert 1 <= r.total <= 20
            assert len(r.rolls) == 2

    def test_advantage_with_modifier(self):
        for _ in range(30):
            r = roll("ad20+5")
            assert 6 <= r.total <= 25


# ---------------------------------------------------------------------------
# Трейсы (dice_trace / expr_trace / dice_count)
# ---------------------------------------------------------------------------

class TestTraces:
    def test_number_traces(self):
        r = roll("42")
        assert r.dice_steps == []
        assert r.expr_trace == "42"
        assert r.dice_count == 0

    def test_single_die_no_step(self, monkeypatch):
        """Одиночный куб не создаёт DiceStep — остаётся инлайн в expr_trace."""
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: 9)
        r = roll("d20")
        assert r.dice_steps == []
        assert r.expr_trace == "[**9**]"
        assert r.dice_count == 1

    def test_multi_dice_creates_step(self, monkeypatch):
        vals = iter([1, 4, 6])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(vals))
        r = roll("3d6")
        assert len(r.dice_steps) == 1
        assert r.dice_steps[0].trace == "[**1**] + [**4**] + [**6**]"
        assert r.dice_steps[0].subtotal == 11
        assert r.expr_trace == "11"
        assert r.dice_count == 3

    def test_add_constant_folds_into_step(self, monkeypatch):
        """3d6+5: константа сворачивается в трейс группы."""
        vals = iter([1, 4, 6])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(vals))
        r = roll("3d6+5")
        assert len(r.dice_steps) == 1
        assert r.dice_steps[0].trace == "[**1**] + [**4**] + [**6**] + 5"
        assert r.dice_steps[0].subtotal == 16

    def test_add_single_die_folds_into_step(self, monkeypatch):
        """3d6+1d8: одиночный куб сворачивается в трейс многокубовой группы."""
        vals = iter([1, 4, 6, 7])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(vals))
        r = roll("3d6+1d8")
        assert len(r.dice_steps) == 1
        assert r.dice_steps[0].trace == "[**1**] + [**4**] + [**6**] + [**7**]"
        assert r.dice_steps[0].subtotal == 18

    def test_add_single_die_trace(self, monkeypatch):
        """d6+3: одиночный куб + константа — нет шага, всё инлайн в expr_trace."""
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: 5)
        r = roll("d6+3")
        assert r.dice_steps == []
        assert r.expr_trace == "[**5**] + 3"
        assert r.dice_count == 1

    def test_mul_single_die_stays_inline(self, monkeypatch):
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: 4)
        r = roll("2*d6")
        assert r.dice_steps == []
        assert "[**4**]" in r.expr_trace
        assert r.dice_count == 1

    def test_mul_with_additive_operand_has_parens(self, monkeypatch):
        """2*(d8+1) не должен терять скобки в expr_trace."""
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: 3)
        r = roll("2*(d8+1)")
        assert r.dice_steps == []
        assert r.expr_trace == "2 * ([**3**] + 1)"

    def test_mul_multi_dice_uses_subtotal(self, monkeypatch):
        vals = iter([2, 7, 9])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(vals))
        r = roll("2*(3d10)")
        assert len(r.dice_steps) == 1
        assert r.dice_steps[0].trace == "[**2**] + [**7**] + [**9**]"
        assert r.dice_steps[0].subtotal == 18
        assert r.expr_trace == "2 * 18"
        assert r.dice_count == 3

    def test_mul_preserves_step_separate_from_outer_add(self, monkeypatch):
        """2*(3d8)+5: +5 снаружи умножения не сворачивается в шаг."""
        vals = iter([1, 2, 1])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(vals))
        r = roll("2*(3d8)+5")
        assert len(r.dice_steps) == 1
        assert r.dice_steps[0].trace == "[**1**] + [**2**] + [**1**]"
        assert r.dice_steps[0].subtotal == 4
        assert r.expr_trace == "2 * 4 + 5"

    def test_multiple_mul_groups_separate_steps(self, monkeypatch):
        """2*(3d8) + 3*(4d10): два независимых mul-контекста → два шага."""
        vals = iter([1, 2, 1, 7, 9, 4, 8])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(vals))
        r = roll("2*(3d8) + 3*(4d10)")
        assert len(r.dice_steps) == 2
        assert r.dice_steps[0].trace == "[**1**] + [**2**] + [**1**]"
        assert r.dice_steps[0].subtotal == 4
        assert r.dice_steps[1].trace == "[**7**] + [**9**] + [**4**] + [**8**]"
        assert r.dice_steps[1].subtotal == 28
        assert r.expr_trace == "2 * 4 + 3 * 28"

    def test_advantage_trace(self, monkeypatch):
        rolls_iter = iter([17, 3])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(rolls_iter))
        r = roll("ad20")
        assert len(r.dice_steps) == 1
        assert r.dice_steps[0].trace == "a[**17**|~~3~~]"
        assert r.expr_trace == "17"

    def test_disadvantage_trace(self, monkeypatch):
        rolls_iter = iter([3, 17])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(rolls_iter))
        r = roll("dd20")
        assert len(r.dice_steps) == 1
        assert r.dice_steps[0].trace == "d[**3**|~~17~~]"
        assert r.expr_trace == "3"


# ---------------------------------------------------------------------------
# Pick (NdXpM)
# ---------------------------------------------------------------------------

class TestPick:
    def test_pick_highest(self, monkeypatch):
        """4d6p2: бросить 4d6, взять 2 наибольших."""
        vals = iter([3, 1, 5, 2])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(vals))
        r = roll("4d6p2")
        assert r.total == 8  # 5 + 3
        assert r.rolls == [3, 1, 5, 2]
        assert r.dice_count == 4

    def test_pick_range(self):
        for _ in range(50):
            r = roll("4d6p3")
            assert 3 <= r.total <= 18

    def test_pick_cyrillic(self):
        for _ in range(50):
            r = roll("4д6п3")
            assert 3 <= r.total <= 18

    def test_pick_trace(self, monkeypatch):
        vals = iter([3, 1, 5, 2])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(vals))
        r = roll("4d6p2")
        assert len(r.dice_steps) == 1
        assert r.dice_steps[0].trace == "[**3**] + ~~1~~ + [**5**] + ~~2~~"
        assert r.dice_steps[0].subtotal == 8

    def test_pick_with_modifier(self, monkeypatch):
        vals = iter([3, 1, 5, 2])
        monkeypatch.setattr("app.dice.evaluator.random.randint", lambda a, b: next(vals))
        r = roll("4d6p2+10")
        assert r.total == 18

    def test_pick_invalid_take_too_high(self):
        r = roll("4d6p4")
        assert r.errors

    def test_pick_invalid_take_zero(self):
        r = roll("4d6p0")
        assert r.errors


# ---------------------------------------------------------------------------
# Валидация и ошибки
# ---------------------------------------------------------------------------

class TestValidation:
    def test_too_many_dice(self):
        r = roll("200d6")
        assert r.errors

    def test_too_few_sides(self):
        r = roll("d0")
        assert r.errors

    def test_too_many_sides(self):
        r = roll("d99999")
        assert r.errors

    def test_invalid_expression(self):
        r = roll("abc")
        assert r.errors

    def test_empty_expression(self):
        r = roll("")
        assert r.errors

    def test_division_preserves_precision(self):
        r = roll("1/3")
        assert r.total == round(1 / 3, 5)
