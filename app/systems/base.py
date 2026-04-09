from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from loguru import logger
from rapidfuzz import fuzz, process

from app.systems.types import ServiceUnavailableError, SpellMatch

ua = UserAgent(browsers=["Chrome", "Firefox", "Safari", "Opera", "Edge"], platforms=["desktop"])

_SPELL_LIST_TTL: int = 86400  # секунды; 24 часа

_log = logger.bind(module="systems")


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

    Подклассы задают ``base_url`` и реализуют ``_fetch_spell_list`` и логику парсинга.
    Предоставляет HTTP-сессию, метод ``_fetch``, кеш списка заклинаний и fuzzy-поиск.

    Attributes:
        base_url: Корневой URL сайта.
    """

    base_url: ClassVar[str]

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._spell_list: dict[str, str] | None = None  # name → slug
        self._spell_list_lower: dict[str, str] | None = None  # name.lower() → slug
        self._spell_list_fetched_at: float | None = None
        self._spell_list_lock: asyncio.Lock = asyncio.Lock()

    @abstractmethod
    async def _fetch_spell_list(self) -> dict[str, str]:
        """Загружает полный список заклинаний сайта.

        Returns:
            Словарь ``{название: slug}``, где slug используется для построения URL страницы.
        """
        ...

    async def _get_spell_list(self) -> dict[str, str]:
        """Возвращает закешированный список заклинаний,
        при необходимости загружает или обновляет его."""
        now = time.monotonic()
        stale = (
            self._spell_list_fetched_at is not None
            and (now - self._spell_list_fetched_at) > _SPELL_LIST_TTL
        )
        if self._spell_list is not None and not stale:
            return self._spell_list
        async with self._spell_list_lock:
            stale = (
                self._spell_list_fetched_at is not None
                and (now - self._spell_list_fetched_at) > _SPELL_LIST_TTL
            )
            if self._spell_list is None or stale:
                _log.debug(f"{self.system_name}: загружаем список заклинаний (stale={stale})")
                spell_list = await self._fetch_spell_list()
                self._spell_list = spell_list
                self._spell_list_lower = {n.lower(): slug for n, slug in spell_list.items()}
                self._spell_list_fetched_at = now
        return self._spell_list

    def _exact_slug(self, name_lower: str) -> str | None:
        """O(1) поиск slug по точному совпадению (без учёта регистра)."""
        return self._spell_list_lower.get(name_lower) if self._spell_list_lower else None

    @staticmethod
    def _fuzzy_match(
        name: str,
        spell_list: dict[str, str],
        *,
        threshold: int = 80,
        limit: int = 10,
    ) -> list[SpellMatch]:
        """Fuzzy-поиск по списку заклинаний.

        Attributes:
            name: Поисковый запрос.
            spell_list: Словарь ``{название: slug}``.
            threshold: Минимальный порог схожести (0–100).
            limit: Максимальное число результатов.

        Returns:
            Список совпадений, отсортированных по убыванию схожести.
        """
        results = process.extract(
            name,
            spell_list.keys(),
            scorer=fuzz.WRatio,
            processor=str.lower,
            score_cutoff=threshold,
            limit=limit,
        )
        return [SpellMatch(name=match, slug=spell_list[match]) for match, _score, _idx in results]

    @staticmethod
    def _get_headers() -> dict[str, str]:
        return {
            "User-Agent": ua.random,
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._get_headers())
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
