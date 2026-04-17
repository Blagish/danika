from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag
from loguru import logger

from app.formatters.table import parse_dnd_su_table, render_table
from app.systems.base import SiteSystemClient
from app.systems.types import SpellMatch

_log = logger.bind(module=__name__)

_INDEX_PATH = "/piece/spells/index-list/"

_SOURCE_TAGS_RE = re.compile(r"(PH14|PH24|TCE|XGE|FTD|SCC|AI)\s*")


@dataclass
class DndSuSpell:
    """Заклинание D&D 5e (источник: dnd.su).

    Attributes:
        name: Название на русском.
        name_en: Название на английском.
        level: Уровень заклинания (0 = заговор).
        school: Школа магии.
        casting_time: Время накладывания.
        spell_range: Дальность.
        components: Компоненты (В, С, М ...).
        duration: Длительность.
        classes: Список классов.
        subclasses: Список подклассов, имеющих доступ.
        description: Основной текст заклинания.
        higher_levels: Текст блока «На больших уровнях», если есть.
        url: Прямая ссылка на страницу заклинания.
        ritual: Может ли быть прочитано как ритуал.
        concentration: Требует ли концентрации.
    """

    name: str
    name_en: str | None
    level: int
    school: str
    casting_time: str
    spell_range: str
    components: str
    duration: str
    classes: list[str]
    description: str
    url: str
    subclasses: list[str] = field(default_factory=list)
    higher_levels: str | None = None
    ritual: bool = False
    concentration: bool = False


class DndSuClient(SiteSystemClient[DndSuSpell]):
    """Клиент для поиска заклинаний D&D 5e на dnd.su."""

    system_name = "D&D 5e (dnd.su)"
    colour = 0xFE650C

    base_url = "https://dnd.su"

    _level_class = "size-type-alignment"

    def __init__(self) -> None:
        super().__init__()
        self._index_url = self.base_url + _INDEX_PATH
        self._slug_to_ru: dict[str, str] = {}
        self._ru_to_en: dict[str, str] = {}  # name.lower() → English name

    async def _fetch_spell_list(self) -> dict[str, str]:
        """Загружает индекс заклинаний из JS-эндпоинта /piece/spells/index-list/.

        Returns:
            Словарь ``{название: slug}`` с русскими и английскими названиями.
        """
        soup = await self._fetch(self._index_url)
        match = None
        for script in soup.find_all("script"):
            match = re.search(r"window\.LIST\s*=\s*(\{.*\})", script.get_text(), re.DOTALL)
            if match:
                break
        if not match:
            _log.error("Не удалось распарсить индекс заклинаний dnd.su")
            return {}

        data = json.loads(match.group(1))
        spells: dict[str, str] = {}
        self._slug_to_ru.clear()
        self._ru_to_en.clear()

        for card in data.get("cards", []):
            title_ru: str = card.get("title", "").strip()
            title_en: str = card.get("title_en", "").strip()
            slug: str = card.get("link", "").strip()

            if not title_ru or not slug:
                continue

            spells[title_ru] = slug
            self._slug_to_ru[slug] = title_ru

            if title_en:
                spells[title_en] = slug
                self._ru_to_en[title_ru.lower()] = title_en

        _log.info(f"{self.system_name}: загружено {len(self._slug_to_ru)} заклинаний")
        return spells

    async def search_spell(self, name: str) -> DndSuSpell | list[SpellMatch] | None:
        """Поиск заклинания по названию с fuzzy-matching.

        Attributes:
            name: Поисковый запрос (на русском или английском).

        Returns:
            DndSuSpell: Единственное совпадение.
            list[SpellMatch]: Несколько кандидатов.
            None: Ничего не найдено.

        Raises:
            ServiceUnavailableError: Сайт недоступен.
        """
        spell_list = await self._get_spell_list()
        exact_slug = self._exact_slug(name.strip().lower())
        if exact_slug:
            return await self.fetch_spell(exact_slug)

        matches = self._fuzzy_match(name, spell_list)
        matches = self._normalize_matches(matches)

        _log.debug(f"fuzzy '{name}': {[(m.name, m.slug) for m in matches]}")

        if not matches:
            return None
        if len(matches) > 1:
            return matches

        return await self.fetch_spell(matches[0].slug)

    def _normalize_matches(self, matches: list[SpellMatch]) -> list[SpellMatch]:
        """Заменяет английские имена на русские и убирает дубликаты по slug."""
        seen: set[str] = set()
        result: list[SpellMatch] = []
        for m in matches:
            if m.slug in seen:
                continue
            seen.add(m.slug)
            ru_name = self._slug_to_ru.get(m.slug, m.name)
            result.append(SpellMatch(name=ru_name, slug=m.slug))
        return result

    async def translate_to_en(self, name: str) -> str | None:
        """Переводит русское название заклинания на английский.

        Attributes:
            name: Название на русском (регистр не важен).

        Returns:
            Английское название, если найдено, иначе ``None``.
        """
        await self._get_spell_list()
        return self._ru_to_en.get(name.strip().lower())

    async def fetch_spell(self, slug: str) -> DndSuSpell:
        """Загружает заклинание по slug.

        Attributes:
            slug: URL-путь заклинания (напр. ``/spells/fireball``).

        Raises:
            ServiceUnavailableError: Сайт недоступен.
        """
        url = f"{self.base_url}{slug}"
        soup = await self._fetch(url)
        return self._parse_spell_page(soup, url)

    # -- парсинг страницы заклинания ------------------------------------------

    def _parse_spell_page(self, soup: BeautifulSoup, url: str) -> DndSuSpell:
        header = soup.find("div", class_="card__header")
        h2 = header.find("h2") if header else None
        raw_title = h2.get_text().strip() if h2 else ""
        name, name_en = self._parse_title(raw_title)

        body = soup.find("div", class_="card__body")
        params = body.find("ul", class_="params") if body else None
        items: list[Tag] = params.find_all("li", recursive=False) if params else []

        level = 0
        school = ""
        casting_time = ""
        spell_range = ""
        components = ""
        duration = ""
        classes: list[str] = []
        subclasses: list[str] = []
        description = ""
        higher_levels: str | None = None
        ritual = False

        for li in items:
            li_classes = li.get("class") or []

            if self._level_class in li_classes:
                level, school, ritual = self._parse_level_school(li.get_text().strip())
                continue

            if "desc" in li_classes:
                desc_div = li.find("div", attrs={"itemprop": "description"})
                if desc_div:
                    description, higher_levels = self._parse_description(desc_div)
                continue

            strong = li.find("strong")
            if not strong:
                continue

            label = strong.get_text().strip().rstrip(":").lower()
            value = li.get_text().replace(strong.get_text(), "", 1).strip()

            if "время" in label:
                casting_time = value
            elif "дистанция" in label or "дальность" in label:
                spell_range = value
            elif "компонент" in label:
                components = value
            elif "длительность" in label:
                duration = value
            elif label == "классы" or label == "класс":
                classes = [c.strip() for c in value.split(",") if c.strip()]
            elif "подкласс" in label:
                subclasses = [c.strip() for c in value.split(",") if c.strip()]

        return DndSuSpell(
            name=name,
            name_en=name_en,
            level=level,
            school=school,
            casting_time=casting_time,
            spell_range=spell_range,
            components=components,
            duration=duration,
            classes=classes,
            subclasses=subclasses,
            description=description,
            url=url,
            higher_levels=higher_levels,
            ritual=ritual,
            concentration="концентрация" in duration.lower(),
        )

    @staticmethod
    def _parse_title(raw: str) -> tuple[str, str | None]:
        """Разбирает «Огненный шар [Fireball]PH14 PH24» в (name, name_en)."""
        cleaned = _SOURCE_TAGS_RE.sub("", raw).strip()
        m = re.match(r"^(.+?)\s*\[(.+?)]\s*$", cleaned)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return cleaned, None

    @staticmethod
    def _parse_level_school(text: str) -> tuple[int, str, bool]:
        """Разбирает «3 уровень, воплощение» или «заговор, воплощение» в (level, school, ritual)."""
        text = text.strip().lower()
        ritual = "ритуал" in text
        text = text.replace("(ритуал)", "").strip()

        if "заговор" in text:
            school = text.replace("заговор", "").strip().strip(",").strip().title()
            return 0, school, ritual

        m = re.match(r"(\d+)\s*уровень\s*,\s*(.+)", text)
        if m:
            return int(m.group(1)), m.group(2).strip().title(), ritual

        return 0, text.title(), ritual

    @staticmethod
    def _parse_description(div: Tag) -> tuple[str, str | None]:
        """Парсит div[itemprop='description'] в (description, higher_levels).

        Поддерживает inline-таблицы вида ``<h4 class="tableTitle">`` + ``<table>``:
        заголовок h4 передаётся в таблицу, она рендерится в Markdown и встраивается
        в описание на своей позиции.
        """
        desc_parts: list[str] = []
        higher_levels: str | None = None
        pending_title: str | None = None

        for el in div.find_all(["p", "h4", "table"], recursive=False):
            if el.name == "h4":
                h4_classes = el.get("class") or []
                if "tableTitle" in h4_classes:
                    pending_title = el.get_text(" ", strip=True) or None
                continue

            if el.name == "table":
                rendered = render_table(parse_dnd_su_table(el, pending_title))
                pending_title = None
                if rendered and higher_levels is None:
                    desc_parts.append(rendered)
                continue

            pending_title = None
            p = el
            text = p.get_text(strip=True)
            if not text:
                continue

            em = p.find("em")
            if em and "на больших уровнях" in em.get_text().lower():
                hl = text
                for prefix in ("На больших уровнях.", "На больших уровнях:"):
                    if hl.startswith(prefix):
                        hl = hl[len(prefix) :].strip()
                higher_levels = hl
                continue

            if higher_levels is None:
                desc_parts.append(text)

        return "\n\n".join(desc_parts), higher_levels


class DndSu2024Client(DndSuClient):
    """Клиент для поиска заклинаний D&D 5e (2024) на next.dnd.su."""

    system_name = "D&D 5e 2024 (dnd.su)"

    base_url = "https://next.dnd.su"

    _level_class = "school_level"

    def __init__(self) -> None:
        super().__init__()
        self._index_url = f"{self.base_url}/spells/"
