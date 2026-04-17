from __future__ import annotations

from dataclasses import dataclass


class ServiceUnavailableError(Exception):
    """Сайт-источник недоступен или вернул ошибку."""

    def __init__(self, host: str, status_code: int | None = None) -> None:
        self.host = host
        self.status_code = status_code
        message = f"Service unavailable: {host}"
        if status_code is not None:
            message += f". Status code: {status_code}"
        super().__init__(message)


@dataclass
class SpellMatch:
    """Потенциальный ответ из нескольких вариантов. Будет уточняться у пользователя.

    Attributes:
        name: Название заклинания.
        slug: Ключ для получения полных данных (путь URL, id и т.п.).
    """

    name: str
    slug: str
