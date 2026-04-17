from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag
from loguru import logger

from app.formatters.table import parse_wikidot_table, render_table
from app.systems.base import SiteSystemClient
from app.systems.types import SpellMatch

_log = logger.bind(module=__name__)

_ORDINALS = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"]


@dataclass
class Dnd5eWikidotSpell:
    """Заклинание D&D 5e (источник: dnd5e.wikidot.com).

    Attributes:
        name: Название на английском.
        level: Уровень заклинания (0 = заговор).
        school: Школа магии.
        casting_time: Время накладывания.
        range: Дальность.
        components: Компоненты (V, S, M ...).
        duration: Длительность.
        classes: Список классов.
        description: Основной текст заклинания.
        higher_levels: Текст блока «At Higher Levels», если есть.
        source: Источник (книга/страница), если есть.
        url: Прямая ссылка на страницу заклинания.
        ritual: Может ли быть прочитано как ритуал.
        concentration: Требует ли концентрации.
    """

    name: str
    level: int
    school: str
    casting_time: str
    range: str
    components: str
    duration: str
    classes: list[str]
    description: str
    url: str
    higher_levels: str | None = None
    source: str | None = None
    ritual: bool = False
    concentration: bool = False


class Dnd5eWikidotClient(SiteSystemClient[Dnd5eWikidotSpell]):
    """Клиент для поиска заклинаний D&D 5e на dnd5e.wikidot.com."""

    system_name = "D&D 5e"
    colour = 0xB22222

    base_url = "https://dnd5e.wikidot.com"

    async def _fetch_spell_list(self) -> dict[str, str]:
        """Загружает полный список заклинаний со страницы /spells.

        Returns:
            Словарь ``{название: slug}``, например ``{"Fireball": "/spell:fireball"}``.
        """
        soup = await self._fetch(f"{self.base_url}/spells")
        spells: dict[str, str] = {}
        for td in soup.find_all("td"):
            if not td.a:
                continue
            name = td.get_text().strip()
            slug = str(td.a["href"])
            if name and slug:
                spells[name] = slug
        _log.info(f"{self.system_name}: загружено {len(spells)} заклинаний")
        return spells

    async def search_spell(self, name: str) -> Dnd5eWikidotSpell | list[SpellMatch] | None:
        """Поиск заклинания по названию с fuzzy-matching.

        Attributes:
            name: Поисковый запрос (название или его часть, опечатки допустимы).

        Returns:
            Dnd5eWikidotSpell: Единственное совпадение.
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
        _log.debug(f"fuzzy '{name}': {[(m.name, m.slug) for m in matches]}")
        if not matches:
            return None
        if len(matches) > 1:
            return matches

        return await self.fetch_spell(matches[0].slug)

    async def fetch_spell(self, slug: str) -> Dnd5eWikidotSpell:
        """Загружает заклинание по slug.

        Attributes:
            slug: URL-путь заклинания (напр. ``/spell:fireball``).

        Raises:
            ServiceUnavailableError: Сайт недоступен.
        """
        spell_url = f"{self.base_url}{slug}"
        soup = await self._fetch(spell_url)
        return self._parse_spell_page(soup, spell_url)

    # -- парсинг страницы заклинания ------------------------------------------

    def _parse_spell_page(self, soup: BeautifulSoup, url: str) -> Dnd5eWikidotSpell:
        title_el = soup.find("div", attrs={"class": "page-title"})
        name = title_el.get_text().strip() if title_el else ""

        card = soup.find("div", attrs={"id": "page-content"})
        elements: list[Tag] = card.find_all(["p", "table"], recursive=False) if card else []

        # Первый <p> — источник ("Source Player's Handbook p. 241").
        source: str | None = None
        rest: list[Tag] = []
        source_taken = False
        for el in elements:
            if not source_taken and el.name == "p":
                raw = el.get_text().strip()
                space_idx = raw.find(" ")
                source = raw[space_idx:].strip() if space_idx != -1 else raw
                source_taken = True
                continue
            rest.append(el)

        level, school, ritual = 0, "", False
        casting_time = range_val = components = duration = ""
        desc_parts: list[str] = []
        higher_levels: str | None = None
        classes: list[str] = []
        in_desc = False

        for el in rest:
            if el.name == "table":
                if in_desc and higher_levels is None:
                    rendered = render_table(parse_wikidot_table(el))
                    if rendered:
                        desc_parts.append(rendered)
                continue

            p = el
            text = p.get_text(" ", strip=True)
            strongs = [s.get_text().lower() for s in p.find_all("strong")]

            # Уровень + школа (курсив)
            em = p.find(["em", "i"])
            if em and not in_desc and not casting_time:
                level, school, ritual = self._parse_level_school(em.get_text())
                continue

            # Блок характеристик
            if any("casting time" in s for s in strongs):
                casting_time = self._field_value(p, "casting time")
                range_val = self._field_value(p, "range")
                components = self._field_value(p, "components")
                duration = self._field_value(p, "duration")
                if "(ritual)" in components.lower() or "(ritual)" in text.lower():
                    ritual = True
                in_desc = True
                continue

            # Список классов
            if text.lower().startswith("spell lists"):
                tail = text.split(".", 1)[-1] if "." in text else text.split(":", 1)[-1]
                classes = [c.strip() for c in tail.split(",") if c.strip()]
                continue

            # At Higher Levels
            if any("at higher level" in s for s in strongs):
                hl = text
                for prefix in ("At Higher Levels.", "At Higher Levels:"):
                    if hl.startswith(prefix):
                        hl = hl[len(prefix) :].strip()
                higher_levels = hl
                continue

            if in_desc and higher_levels is None and text:
                desc_parts.append(text)

        return Dnd5eWikidotSpell(
            name=name,
            level=level,
            school=school,
            casting_time=casting_time,
            range=range_val,
            components=components,
            duration=duration,
            classes=classes,
            description="\n\n".join(desc_parts),
            url=url,
            higher_levels=higher_levels,
            source=source,
            ritual=ritual,
            concentration="concentration" in duration.lower(),
        )

    @staticmethod
    def _parse_level_school(text: str) -> tuple[int, str, bool]:
        """Разбирает «3rd-level evocation» или «Evocation cantrip» в (level, school, ritual)."""
        text = text.strip().lower()
        ritual = "(ritual)" in text
        if "cantrip" in text:
            school = text.replace("cantrip", "").replace("(ritual)", "").strip().title()
            return 0, school, ritual
        for i, ordinal in enumerate(_ORDINALS, 1):
            if f"{ordinal}-level" in text:
                school = text.split("level", 1)[-1].replace("(ritual)", "").strip().title()
                return i, school, ritual
        return 0, text.title(), ritual

    @staticmethod
    def _field_value(p: Tag, field: str) -> str:
        """Возвращает текст после <strong>-метки поля внутри параграфа."""
        for strong in p.find_all("strong"):
            if field in strong.get_text().lower():
                parts: list[str] = []
                for sib in strong.next_siblings:
                    if isinstance(sib, Tag):
                        if sib.name == "strong":
                            break
                        if sib.name == "br":
                            break
                        parts.append(sib.get_text())
                    else:
                        parts.append(str(sib))
                return "".join(parts).strip().strip(",").strip()
        return ""


class Dnd2024WikidotClient(Dnd5eWikidotClient):
    """Клиент для поиска заклинаний D&D 5e (2024) на dnd2024.wikidot.com."""

    system_name = "D&D 5e (2024)"

    base_url = "http://dnd2024.wikidot.com"

    def _parse_spell_page(self, soup: BeautifulSoup, url: str) -> Dnd5eWikidotSpell:
        title_el = soup.find("div", attrs={"class": "page-title"})
        name = title_el.get_text().strip() if title_el else ""

        card = soup.find("div", attrs={"id": "page-content"})
        elements: list[Tag] = card.find_all(["p", "table"], recursive=False) if card else []

        source: str | None = None
        rest: list[Tag] = []
        source_taken = False
        for el in elements:
            if not source_taken and el.name == "p":
                raw = el.get_text().strip()
                if raw.lower().startswith("source:"):
                    source = raw[len("source:") :].strip()
                elif raw.lower().startswith("source"):
                    source = raw[len("source") :].strip()
                source_taken = True
                continue
            rest.append(el)

        level, school, ritual = 0, "", False
        casting_time = range_val = components = duration = ""
        desc_parts: list[str] = []
        higher_levels: str | None = None
        classes: list[str] = []
        in_desc = False

        for el in rest:
            if el.name == "table":
                if in_desc and higher_levels is None:
                    rendered = render_table(parse_wikidot_table(el))
                    if rendered:
                        desc_parts.append(rendered)
                continue

            p = el
            text = p.get_text(" ", strip=True)
            strongs = [s.get_text().lower() for s in p.find_all("strong")]

            # Уровень + школа + классы (курсив)
            em = p.find(["em", "i"])
            if em and not in_desc and not casting_time:
                level, school, classes = self._parse_level_school_2024(em.get_text())
                continue

            # Блок характеристик
            if any("casting time" in s for s in strongs):
                casting_time = self._field_value(p, "casting time")
                range_val = self._field_value(p, "range")
                components = self._field_value(p, "components")
                duration = self._field_value(p, "duration")
                ritual = "ritual" in casting_time.lower()
                in_desc = True
                continue

            # Using a Higher-Level Spell Slot / Cantrip Upgrade
            if any(k in s for s in strongs for k in ("higher-level spell slot", "cantrip upgrade")):
                hl = text
                for prefix in (
                    "Using a Higher-Level Spell Slot.",
                    "Using a Higher-Level Spell Slot:",
                    "Cantrip Upgrade.",
                    "Cantrip Upgrade:",
                ):
                    if hl.startswith(prefix):
                        hl = hl[len(prefix) :].strip()
                higher_levels = hl
                continue

            if in_desc and higher_levels is None and text:
                desc_parts.append(text)

        return Dnd5eWikidotSpell(
            name=name,
            level=level,
            school=school,
            casting_time=casting_time,
            range=range_val,
            components=components,
            duration=duration,
            classes=classes,
            description="\n\n".join(desc_parts),
            url=url,
            higher_levels=higher_levels,
            source=source,
            ritual=ritual,
            concentration="concentration" in duration.lower(),
        )

    @staticmethod
    def _parse_level_school_2024(text: str) -> tuple[int, str, list[str]]:
        """Разбирает «Level 3 Evocation (Sorcerer, Wizard)» или «Evocation Cantrip (...)»."""
        text = text.strip()

        # Классы в скобках
        classes: list[str] = []
        m_classes = re.search(r"\(([^)]+)\)", text)
        if m_classes:
            classes = [c.strip() for c in m_classes.group(1).split(",") if c.strip()]
            text = text[: m_classes.start()].strip()

        text_lower = text.lower()

        # "Evocation Cantrip"
        if "cantrip" in text_lower:
            school = text_lower.replace("cantrip", "").strip().title()
            return 0, school, classes

        # "Level 3 Evocation"
        m = re.match(r"level\s+(\d+)\s+(.+)", text_lower)
        if m:
            return int(m.group(1)), m.group(2).strip().title(), classes

        return 0, text.title(), classes
