from __future__ import annotations

from bs4 import BeautifulSoup

from app.formatters.table import (
    TableBlock,
    parse_dnd_su_table,
    parse_wikidot_table,
    render_table,
)

# ---------------------------------------------------------------------------
# render_table — логика выбора формата
# ---------------------------------------------------------------------------


class TestRenderTable:
    """Тесты авто-выбора формата рендера."""

    def test_empty_rows_returns_empty_string(self) -> None:
        block = TableBlock(title="X", headers=["a", "b"], rows=[])
        assert render_table(block) == ""

    def test_two_col_narrative(self) -> None:
        long_text = "The smell of apple pie fills the air, charming all creatures."
        block = TableBlock(
            title=None,
            headers=["d4", "Effect"],
            rows=[["1", long_text], ["2", "Another long effect text exceeding limit."]],
        )
        out = render_table(block)
        assert "**1**" in out
        assert " — " in out
        assert long_text in out
        # Курсивная шапка.
        assert "*d4 · Effect*" in out

    def test_three_col_narrative(self) -> None:
        block = TableBlock(
            title="Item Quirks",
            headers=["d10", "Quirk", "Description"],
            rows=[
                ["1", "Cavorting", "Dances in place when not in use, hopping around."],
                ["2", "Clean", "Remains pristine despite filth in the surroundings."],
            ],
        )
        out = render_table(block)
        assert out.startswith("**Item Quirks**")
        assert "**1 · Cavorting**" in out
        assert " — Dances in place" in out

    def test_five_col_short_codeblock(self) -> None:
        block = TableBlock(
            title=None,
            headers=["Lv", "HP", "AC", "DC", "Dmg"],
            rows=[
                ["1", "10", "13", "12", "1d6"],
                ["2", "18", "14", "13", "2d6"],
            ],
        )
        out = render_table(block)
        assert out.startswith("```")
        assert out.endswith("```")
        # Выравнивание колонок пробелами.
        lines = out.split("\n")
        assert any("Lv" in line and "HP" in line for line in lines)

    def test_wide_all_short_falls_back_to_block_per_row(self) -> None:
        # 5 колонок, данные среднего размера — сумма > 28, narrative нет.
        block = TableBlock(
            title=None,
            headers=["Level", "Creature", "HP", "Speed", "Special"],
            rows=[
                ["6th", "Young Brass Dragon", "110", "40 ft", "Breath weapon"],
                ["7th", "Adult Brass Dragon", "220", "40 ft", "Frightful presence"],
            ],
        )
        out = render_table(block)
        assert "```" not in out
        assert "**6th**" in out
        assert "Creature: Young Brass Dragon" in out

    def test_title_rendered_bold_first_line(self) -> None:
        block = TableBlock(
            title="Mischievous Surge",
            headers=["d4", "Effect"],
            rows=[["1", "x" * 50]],
        )
        out = render_table(block)
        assert out.split("\n", 1)[0] == "**Mischievous Surge**"

    def test_no_headers_ok(self) -> None:
        block = TableBlock(
            title=None,
            headers=[],
            rows=[["1", "A very long narrative description of some effect occurring."]],
        )
        out = render_table(block)
        assert "**1**" in out
        assert " — A very long narrative" in out
        # Курсивная шапка столбцов не рендерится — нет строки, начинающейся с одиночного `*`.
        assert not any(
            line.startswith("*") and not line.startswith("**") for line in out.split("\n")
        )

    def test_single_column_table_renders_rows_plainly(self) -> None:
        # Только один столбец — нет label, body = единственная ячейка.
        block = TableBlock(
            title=None,
            headers=["Effect"],
            rows=[["A" * 50], ["B" * 50]],
        )
        out = render_table(block)
        # Не должно быть "** ** — ..."
        assert "** **" not in out
        assert out.count("A" * 50) == 1


# ---------------------------------------------------------------------------
# parse_wikidot_table
# ---------------------------------------------------------------------------


class TestParseWikidotTable:
    """Тесты парсинга HTML-таблицы wikidot."""

    def test_colspan_title_and_headers(self) -> None:
        html = """
        <table class="wiki-content-table">
          <tr><th colspan="2"><strong>Mischievous Surge</strong></th></tr>
          <tr><th><strong>d4</strong></th><th><strong>Effect</strong></th></tr>
          <tr><td>1</td><td>Apple pie smell.</td></tr>
          <tr><td>2</td><td>Flowers bloom.</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        assert table is not None
        block = parse_wikidot_table(table)
        assert block.title == "Mischievous Surge"
        assert block.headers == ["d4", "Effect"]
        assert block.rows == [["1", "Apple pie smell."], ["2", "Flowers bloom."]]

    def test_no_title_no_headers(self) -> None:
        html = """
        <table>
          <tr><td>1</td><td>A</td></tr>
          <tr><td>2</td><td>B</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        assert table is not None
        block = parse_wikidot_table(table)
        assert block.title is None
        assert block.headers == []
        assert block.rows == [["1", "A"], ["2", "B"]]


# ---------------------------------------------------------------------------
# parse_dnd_su_table
# ---------------------------------------------------------------------------


class TestParseDndSuTable:
    """Тесты парсинга HTML-таблицы dnd.su."""

    def test_with_external_title_and_header_class(self) -> None:
        html = """
        <table>
          <tbody>
            <tr class="table_header"><td>к4</td><td>Эффект</td></tr>
            <tr><td>1</td><td>Запах яблочного пирога.</td></tr>
            <tr><td>2</td><td>Букеты цветов.</td></tr>
          </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        assert table is not None
        block = parse_dnd_su_table(table, title="Озорной порыв")
        assert block.title == "Озорной порыв"
        assert block.headers == ["к4", "Эффект"]
        assert block.rows == [
            ["1", "Запах яблочного пирога."],
            ["2", "Букеты цветов."],
        ]

    def test_inline_span_tooltips_extracted_as_text(self) -> None:
        html = """
        <table>
          <tbody>
            <tr class="table_header"><td>к4</td><td>Эффект</td></tr>
            <tr><td>1</td><td>Существо <span title="x">ослеплено</span> до конца хода.</td></tr>
          </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        assert table is not None
        block = parse_dnd_su_table(table, title=None)
        assert block.rows[0][1] == "Существо ослеплено до конца хода."

    def test_no_title_no_headers(self) -> None:
        html = """
        <table>
          <tbody>
            <tr><td>1</td><td>A</td></tr>
          </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        assert table is not None
        block = parse_dnd_su_table(table, title=None)
        assert block.title is None
        assert block.headers == []
        assert block.rows == [["1", "A"]]
