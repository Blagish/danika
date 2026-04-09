from __future__ import annotations

from discord import Colour, Embed

from app.systems.types import SpellMatch


def format_spell_choices(choices: list[SpellMatch]) -> Embed:
    """Найдено несколько вариантов ответа"""
    listing = "\n".join(f"- {m.name}" for m in choices)
    return Embed(
        title="┗( T﹏T )┛ у меня несколько ответов!",
        description=f"Уточните запрос из списка:\n{listing}",
        colour=Colour.gold(),
    )


def format_not_found(query: str) -> Embed:
    """Запрос не дал результатов"""
    return Embed(
        title="OwO, what's this?",
        description=f'По вашему запросу "{query}" ничего не найдено.',
        colour=Colour.red(),
    )


def format_too_short() -> Embed:
    """Слишком короткий запрос"""
    return Embed(
        title="You baka!",
        description="Поисковой запрос должен быть не менее 3 символа.",
        colour=Colour.red(),
    )


def format_service_error(host: str) -> Embed:
    """Сервис недоступен"""
    return Embed(
        title="никто не пришел на фан встречу :(",
        description=f"`{host}` не отвечает. Попробуйте позже.",
        colour=Colour.red(),
    )
