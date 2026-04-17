"""Общие утилиты для CLI-скриптов."""

from __future__ import annotations

import re


def render_embed(embed: object) -> str:
    """Рендерит Discord Embed в plain text для вывода в терминал."""
    parts = []
    if title := getattr(embed, "title", None):
        parts.append(title)
    if desc := getattr(embed, "description", None):
        parts.append(desc)
    for field in getattr(embed, "fields", []):
        parts.append(f"\n{field.name}: {field.value}")
    return "\n".join(parts)


def strip_markdown(text: str) -> str:
    """Убирает Discord markdown (bold, italic, code) для вывода в терминал."""
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
    text = text.replace("`", "")
    return text
