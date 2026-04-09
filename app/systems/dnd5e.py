from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from app.systems.base import SiteSystemClient
from app.systems.types import SpellMatch

_ORDINALS = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"]


@dataclass
class Dnd5eSpell:
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


class Dnd5eClient(SiteSystemClient[Dnd5eSpell]):
    """Клиент для поиска заклинаний D&D 5e на dnd5e.wikidot.com."""

    system_name = "D&D 5e"
    colour = 0xB22222

    base_url = "https://dnd5e.wikidot.com"
    search_url = "https://dnd5e.wikidot.com/spells"

    async def search_spell(self, name: str) -> Dnd5eSpell | list[SpellMatch] | None:
        """Поиск заклинания по названию.

        Attributes:
            name: Поисковый запрос (название или его часть).

        Returns:
            Dnd5eSpell: Точное совпадение.
            list[SpellMatch]: Несколько кандидатов.
            None: Ничего не найдено.

        Raises:
            ServiceUnavailableError: Сайт недоступен.
        """
        search_soup = await self._fetch(self.search_url, search=name)
        name_lower = name.strip().lower()

        # <td> ячейки с ссылками на заклинания, в тексте которых есть запрос
        results: list[Tag] = search_soup.find_all(
            lambda tag: tag and tag.name == "td" and tag.a and name_lower in tag.get_text().lower()
        )

        if not results:
            return None

        # Точное совпадение → берём сразу
        exact = [r for r in results if r.get_text().strip().lower() == name_lower]
        if exact:
            chosen = exact[0]
        elif len(results) == 1:
            chosen = results[0]
        else:
            # Несколько вариантов → дизамбигуация
            return [SpellMatch(name=t.get_text().strip(), slug=t.a["href"]) for t in results[:10]]

        href: str = chosen.a["href"]  # e.g. "spell:fireball"
        spell_url = f"{self.base_url}/{href}"
        spell_soup = await self._fetch(spell_url)
        return self._parse_spell_page(spell_soup, spell_url)

    # -- парсинг страницы заклинания ------------------------------------------

    def _parse_spell_page(self, soup: BeautifulSoup, url: str) -> Dnd5eSpell:
        title_el = soup.find("div", attrs={"class": "page-title"})
        name = title_el.get_text().strip() if title_el else ""
        # ua = "(UA)" in name

        card = soup.find("div", attrs={"id": "page-content"})
        ps: list[Tag] = card.find_all("p") if card else []

        # Первый <p> — источник ("Source Player's Handbook p. 241")
        source: str | None = None
        if ps:
            raw = ps[0].get_text().strip()
            space_idx = raw.find(" ")
            source = raw[space_idx:].strip() if space_idx != -1 else raw

        level, school, ritual = 0, "", False
        casting_time = range_val = components = duration = ""
        desc_parts: list[str] = []
        higher_levels: str | None = None
        classes: list[str] = []
        in_desc = False

        for p in ps[1:]:
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

        return Dnd5eSpell(
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
