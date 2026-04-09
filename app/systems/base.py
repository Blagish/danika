from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

import aiohttp
from bs4 import BeautifulSoup

from app.systems.types import ServiceUnavailableError, SpellMatch


class SystemClient[T](ABC):
    """Абстрактный базовый класс для клиентов игровых систем.

    Параметр типа ``T`` — конкретный датакласс заклинания для данной системы.

    Attributes:
        system_name: Читаемое название системы (напр. "D&D 5e").
        colour: Цвет эмбеда по умолчанию для этой системы.
    """

    system_name: ClassVar[str]
    colour: ClassVar[int]

    @abstractmethod
    async def search_spell(self, name: str) -> T | list[SpellMatch] | None:
        """Поиск заклинания по имени.

        Returns:
            T: Найдено точное совпадение.
            list[SpellMatch]: Несколько кандидатов — вызывающий должен уточнить.
            None: Ничего не найдено.

        Raises:
            ServiceUnavailableError: Сайт-источник не отвечает.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Освобождает ресурсы. Переопределяется в подклассах с сессиями."""
        ...


class SiteSystemClient[T](SystemClient[T], ABC):
    """Базовый класс для клиентов, скрапящих HTML-страницы.

    Подклассы задают ``base_url``, ``search_url`` и реализуют логику парсинга.
    Предоставляет async HTTP-сессию и метод ``_fetch`` для получения страниц.

    Attributes:
        base_url: Корневой URL сайта.
        search_url: URL для поисковых запросов.
    """

    base_url: ClassVar[str]
    search_url: ClassVar[str]

    _headers: ClassVar[dict[str, str]] = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._headers)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _fetch(self, url: str, **params: Any) -> BeautifulSoup:
        """GET *url* и вернуть распарсенный HTML.

        Raises:
            ServiceUnavailableError: При любой HTTP- или сетевой ошибке.
        """
        session = await self._get_session()
        try:
            async with session.get(url, params=params or None) as resp:
                if resp.status != 200:
                    raise ServiceUnavailableError(self.base_url, resp.status)
                html = await resp.text()
        except aiohttp.ClientError as exc:
            raise ServiceUnavailableError(self.base_url) from exc
        return BeautifulSoup(html, "html.parser")
