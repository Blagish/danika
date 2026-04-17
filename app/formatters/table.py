from __future__ import annotations

from dataclasses import dataclass

from bs4 import Tag

_NARRATIVE_THRESHOLD: int = 40
_CODE_BLOCK_WIDTH_BUDGET: int = 28
_BLOCK_ROW_INLINE_LIMIT: int = 60
_LABEL_SEP: str = " · "
_NARRATIVE_SEP: str = " — "


@dataclass(frozen=True)
class TableBlock:
    """Представление HTML-таблицы для Discord-рендера.

    Attributes:
        title: Заголовок таблицы (bold-строкой сверху), если указан.
        headers: Заголовки столбцов; пустой список, если их не было.
        rows: Двумерный массив ячеек-строк.
    """

    title: str | None
    headers: list[str]
    rows: list[list[str]]


def parse_wikidot_table(table: Tag) -> TableBlock:
    """Разбирает <table class='wiki-content-table'> с wikidot в TableBlock.

    Attributes:
        table: Тег ``<table>`` со страницы заклинания wikidot.

    Structure:
        * Первая ``<tr>`` с ``<th colspan>`` — заголовок таблицы.
        * Следующая ``<tr>`` из одних ``<th>`` — шапка столбцов.
        * Остальные ``<tr>`` из ``<td>`` — строки данных.
    """
    title: str | None = None
    headers: list[str] = []
    rows: list[list[str]] = []

    for tr in table.find_all("tr", recursive=True):
        cells = tr.find_all(["th", "td"], recursive=False)
        if not cells:
            continue

        # Заголовок таблицы: первая строка с colspan.
        if title is None and not headers and not rows:
            first = cells[0]
            if first.name == "th" and first.get("colspan"):
                title = first.get_text(" ", strip=True)
                continue

        # Шапка столбцов: все ячейки — <th>.
        if not headers and not rows and all(c.name == "th" for c in cells):
            headers = [c.get_text(" ", strip=True) for c in cells]
            continue

        row = [c.get_text(" ", strip=True) for c in cells]
        if any(cell for cell in row):
            rows.append(row)

    return TableBlock(title=title, headers=headers, rows=rows)


def parse_dnd_su_table(table: Tag, title: str | None) -> TableBlock:
    """Разбирает ``<table>`` с dnd.su в TableBlock.

    Attributes:
        table: Тег ``<table>`` из блока описания заклинания.
        title: Текст из предшествующего ``<h4 class="tableTitle">``
            (заголовок передаётся извне, т. к. в DOM он — соседний элемент).

    Structure:
        * Шапка столбцов — первая ``<tr class="table_header">`` из ``<td>``.
        * Остальные ``<tr>`` — строки данных.
    """
    headers: list[str] = []
    rows: list[list[str]] = []

    for tr in table.find_all("tr", recursive=True):
        cells = tr.find_all(["th", "td"], recursive=False)
        if not cells:
            continue

        row = [c.get_text(" ", strip=True) for c in cells]
        tr_classes = tr.get("class") or []

        if not headers and not rows and "table_header" in tr_classes:
            headers = row
            continue

        if any(cell for cell in row):
            rows.append(row)

    return TableBlock(title=title, headers=headers, rows=rows)


def render_table(block: TableBlock) -> str:
    """Рендерит TableBlock в Discord-Markdown.

    Attributes:
        block: Представление таблицы.

    Algorithm:
        1. Пустая таблица → ``""``.
        2. Последний столбец с max-ячейкой > 40 симв → narrative-формат:
           ``**col_0 · … · col_{n-2}** — col_{n-1}`` построчно.
        3. Иначе если ``sum(max_widths) + 2·(n-1) ≤ 28`` → ``code block``.
        4. Иначе block-per-row с ``key: value``.
        5. ``title`` (если есть) выносится bold-строкой сверху.
        6. ``headers`` в narrative/block-per-row — курсивной строкой;
           в code block — первой строкой таблицы.
    """
    if not block.rows:
        return ""

    n_cols = max(len(row) for row in block.rows)
    rows = [row + [""] * (n_cols - len(row)) for row in block.rows]
    headers_padded: list[str] = (
        block.headers + [""] * (n_cols - len(block.headers)) if block.headers else [""] * n_cols
    )

    max_widths = [max(len(row[i]) for row in rows) for i in range(n_cols)]
    if block.headers:
        max_widths = [max(max_widths[i], len(headers_padded[i])) for i in range(n_cols)]

    lines: list[str] = []
    if block.title:
        lines.append(f"**{block.title}**")

    narrative = n_cols >= 2 and max_widths[-1] > _NARRATIVE_THRESHOLD

    if narrative:
        _append_header_italic(lines, block.headers)
        for row in rows:
            label = _LABEL_SEP.join(row[:-1])
            body = row[-1]
            lines.append(f"**{label}**{_NARRATIVE_SEP}{body}" if label else body)
        return "\n".join(lines)

    sep_width = 2 * (n_cols - 1) if n_cols > 1 else 0
    total_width = sum(max_widths) + sep_width
    if total_width <= _CODE_BLOCK_WIDTH_BUDGET:
        lines.append("```")
        if block.headers and any(h for h in headers_padded):
            lines.append("  ".join(headers_padded[i].ljust(max_widths[i]) for i in range(n_cols)))
        for row in rows:
            lines.append("  ".join(row[i].ljust(max_widths[i]) for i in range(n_cols)))
        lines.append("```")
        return "\n".join(lines)

    # Block-per-row.
    _append_header_italic(lines, block.headers)
    for row in rows:
        lines.append(f"**{row[0]}**")
        if block.headers:
            pairs = [f"{headers_padded[i]}: {row[i]}" for i in range(1, n_cols) if row[i]]
        else:
            pairs = [row[i] for i in range(1, n_cols) if row[i]]
        one_line = _LABEL_SEP.join(pairs)
        if len(one_line) <= _BLOCK_ROW_INLINE_LIMIT:
            if one_line:
                lines.append(one_line)
        else:
            lines.extend(pairs)

    return "\n".join(lines)


def _append_header_italic(lines: list[str], headers: list[str]) -> None:
    """Добавляет курсивную строку заголовков столбцов, если они информативны."""
    if not headers:
        return
    meaningful = [h for h in headers if h]
    if not meaningful:
        return
    lines.append(f"*{_LABEL_SEP.join(meaningful)}*")
