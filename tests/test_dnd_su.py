from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from bs4 import BeautifulSoup

from app.systems.dnd5e_dnd_su import DndSu2024Client, DndSuClient, DndSuSpell
from app.systems.types import SpellMatch

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / name).read_text(), "html.parser")


# ---------------------------------------------------------------------------
# _parse_title
# ---------------------------------------------------------------------------


class TestParseTitle:
    """Разбор строки заголовка вида «Огненный шар [Fireball]PH14 PH24»."""

    parse = staticmethod(DndSuClient._parse_title)

    def test_basic(self) -> None:
        assert self.parse("Огненный шар [Fireball]PH14 PH24") == (
            "Огненный шар",
            "Fireball",
        )

    def test_no_source_tags(self) -> None:
        assert self.parse("Огненный шар [Fireball]") == ("Огненный шар", "Fireball")

    def test_no_english_name(self) -> None:
        assert self.parse("Огненный шар") == ("Огненный шар", None)

    def test_single_source_tag(self) -> None:
        assert self.parse("Щит [Shield]XGE") == ("Щит", "Shield")

    def test_strips_whitespace(self) -> None:
        name, name_en = self.parse("  Щит  [ Shield ] PH14 ")
        assert name == "Щит"
        assert name_en == "Shield"


# ---------------------------------------------------------------------------
# _parse_level_school
# ---------------------------------------------------------------------------


class TestParseLevelSchool:
    """Разбор строки уровня и школы магии (русский формат)."""

    parse = staticmethod(DndSuClient._parse_level_school)

    def test_numbered_level(self) -> None:
        assert self.parse("3 уровень, воплощение") == (3, "Воплощение", False)

    def test_cantrip(self) -> None:
        level, school, ritual = self.parse("заговор, воплощение")
        assert level == 0
        assert school == "Воплощение"
        assert ritual is False

    def test_ritual(self) -> None:
        level, school, ritual = self.parse("1 уровень, прорицание (ритуал)")
        assert level == 1
        assert school == "Прорицание"
        assert ritual is True

    def test_all_levels(self) -> None:
        for i in range(1, 10):
            level, _, _ = self.parse(f"{i} уровень, отречение")
            assert level == i


# ---------------------------------------------------------------------------
# _parse_spell_page — парсинг замороженных HTML-страниц
# ---------------------------------------------------------------------------


class TestParseSpellPage:
    """Тесты парсинга HTML-страницы заклинания."""

    client = DndSuClient()

    def test_fireball_basics(self) -> None:
        soup = _load("dnd_su_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd.su/spells/205-fireball/")

        assert isinstance(spell, DndSuSpell)
        assert spell.name == "Огненный шар"
        assert spell.name_en == "Fireball"
        assert spell.level == 3
        assert spell.school == "Воплощение"
        assert spell.ritual is False
        assert spell.concentration is False

    def test_fireball_stats(self) -> None:
        soup = _load("dnd_su_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd.su/spells/205-fireball/")

        assert spell.casting_time == "1 действие"
        assert spell.spell_range == "150 футов"
        assert "гуано" in spell.components
        assert spell.duration == "Мгновенная"

    def test_fireball_higher_levels(self) -> None:
        soup = _load("dnd_su_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd.su/spells/205-fireball/")

        assert spell.higher_levels is not None
        assert "1к6" in spell.higher_levels

    def test_fireball_classes(self) -> None:
        soup = _load("dnd_su_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd.su/spells/205-fireball/")

        assert "чародей" in spell.classes
        assert "волшебник" in spell.classes

    def test_fireball_subclasses(self) -> None:
        soup = _load("dnd_su_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd.su/spells/205-fireball/")

        assert len(spell.subclasses) > 0
        assert any("свет" in s for s in spell.subclasses)

    def test_fireball_description(self) -> None:
        soup = _load("dnd_su_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd.su/spells/205-fireball/")

        assert "8к6" in spell.description

    def test_fireball_url(self) -> None:
        soup = _load("dnd_su_fireball.html")
        url = "https://dnd.su/spells/205-fireball/"
        spell = self.client._parse_spell_page(soup, url)

        assert spell.url == url

    def test_cantrip_fire_bolt(self) -> None:
        soup = _load("dnd_su_fire_bolt.html")
        spell = self.client._parse_spell_page(soup, "https://dnd.su/spells/204-fire-bolt/")

        assert spell.name == "Огненный снаряд"
        assert spell.level == 0
        assert spell.school == "Воплощение"
        assert spell.higher_levels is None

    def test_ritual_detect_magic(self) -> None:
        soup = _load("dnd_su_detect_magic.html")
        spell = self.client._parse_spell_page(soup, "https://dnd.su/spells/195-detect-magic/")

        assert spell.name == "Обнаружение магии"
        assert spell.name_en == "Detect magic"
        assert spell.level == 1
        assert spell.school == "Прорицание"
        assert spell.ritual is True
        assert spell.concentration is True
        assert "Концентрация" in spell.duration

    def test_detect_magic_subclasses(self) -> None:
        soup = _load("dnd_su_detect_magic.html")
        spell = self.client._parse_spell_page(soup, "https://dnd.su/spells/195-detect-magic/")

        assert len(spell.subclasses) > 0


# ---------------------------------------------------------------------------
# search_spell — интеграция с замоканным _fetch
# ---------------------------------------------------------------------------


class TestSearchSpell:
    """Тесты поиска заклинания (HTTP замокан через фикстуры)."""

    @pytest.mark.asyncio
    async def test_exact_match_ru(self) -> None:
        client = DndSuClient()
        index_soup = _load("dnd_su_index.html")
        spell_soup = _load("dnd_su_fireball.html")

        with patch.object(
            client, "_fetch", new_callable=AsyncMock, side_effect=[index_soup, spell_soup]
        ):
            result = await client.search_spell("Огненный шар")

        assert isinstance(result, DndSuSpell)
        assert result.name == "Огненный шар"

    @pytest.mark.asyncio
    async def test_exact_match_en(self) -> None:
        client = DndSuClient()
        index_soup = _load("dnd_su_index.html")
        spell_soup = _load("dnd_su_fireball.html")

        with patch.object(
            client, "_fetch", new_callable=AsyncMock, side_effect=[index_soup, spell_soup]
        ):
            result = await client.search_spell("Fireball")

        assert isinstance(result, DndSuSpell)
        assert result.name == "Огненный шар"

    @pytest.mark.asyncio
    async def test_disambiguation(self) -> None:
        client = DndSuClient()
        index_soup = _load("dnd_su_index.html")

        with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=index_soup):
            result = await client.search_spell("огненн")

        assert isinstance(result, list)
        assert all(isinstance(m, SpellMatch) for m in result)
        assert len(result) > 1

    @pytest.mark.asyncio
    async def test_disambiguation_all_russian_names(self) -> None:
        """Все имена в списке дизамбигуации — русские."""
        client = DndSuClient()
        index_soup = _load("dnd_su_index.html")

        with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=index_soup):
            result = await client.search_spell("fire")

        assert isinstance(result, list)
        for m in result:
            assert isinstance(m, SpellMatch)
            assert any("а" <= c <= "я" or "А" <= c <= "Я" for c in m.name)

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        client = DndSuClient()
        index_soup = _load("dnd_su_index.html")

        with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=index_soup):
            result = await client.search_spell("xyznonexistent")

        assert result is None


# ---------------------------------------------------------------------------
# translate_to_en
# ---------------------------------------------------------------------------


class TestTranslateToEn:
    """Тесты перевода русских названий в английские."""

    @pytest.mark.asyncio
    async def test_known_spell(self) -> None:
        client = DndSuClient()
        index_soup = _load("dnd_su_index.html")

        with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=index_soup):
            result = await client.translate_to_en("Огненный шар")

        assert result == "Fireball"

    @pytest.mark.asyncio
    async def test_case_insensitive(self) -> None:
        client = DndSuClient()
        index_soup = _load("dnd_su_index.html")

        with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=index_soup):
            result = await client.translate_to_en("огненный шар")

        assert result == "Fireball"

    @pytest.mark.asyncio
    async def test_unknown_returns_none(self) -> None:
        client = DndSuClient()
        index_soup = _load("dnd_su_index.html")

        with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=index_soup):
            result = await client.translate_to_en("Несуществующее заклинание")

        assert result is None


# ===========================================================================
# DndSu2024Client
# ===========================================================================


class TestParseSpellPage2024:
    """Парсинг HTML-страниц заклинаний с next.dnd.su."""

    client = DndSu2024Client()

    def test_hunters_mark_basics(self) -> None:
        soup = _load("dnd_su24_hunters_mark.html")
        spell = self.client._parse_spell_page(soup, "https://next.dnd.su/spells/10195-hunters-mark")

        assert isinstance(spell, DndSuSpell)
        assert spell.name == "Метка охотника"
        assert spell.name_en == "Hunter's Mark"
        assert spell.level == 1
        assert spell.school == "Прорицание"

    def test_hunters_mark_stats(self) -> None:
        soup = _load("dnd_su24_hunters_mark.html")
        spell = self.client._parse_spell_page(soup, "https://next.dnd.su/spells/10195-hunters-mark")

        assert "Бонусное действие" in spell.casting_time
        assert spell.spell_range == "90 футов"
        assert spell.concentration is True

    def test_hunters_mark_classes(self) -> None:
        soup = _load("dnd_su24_hunters_mark.html")
        spell = self.client._parse_spell_page(soup, "https://next.dnd.su/spells/10195-hunters-mark")

        assert "Следопыт" in spell.classes
        assert len(spell.subclasses) > 0

    def test_cantrip_fire_bolt(self) -> None:
        soup = _load("dnd_su24_fire_bolt.html")
        spell = self.client._parse_spell_page(soup, "https://next.dnd.su/spells/10511-fire-bolt")

        assert spell.name == "Огненный снаряд"
        assert spell.name_en == "Fire Bolt"
        assert spell.level == 0
        assert spell.school == "Воплощение"


class TestSearchSpell2024Ru:
    """Тесты поиска заклинания на next.dnd.su."""

    @pytest.mark.asyncio
    async def test_exact_match(self) -> None:
        client = DndSu2024Client()
        index_soup = _load("dnd_su24_index.html")
        spell_soup = _load("dnd_su24_hunters_mark.html")

        with patch.object(
            client, "_fetch", new_callable=AsyncMock, side_effect=[index_soup, spell_soup]
        ):
            result = await client.search_spell("Метка охотника")

        assert isinstance(result, DndSuSpell)
        assert result.name == "Метка охотника"

    @pytest.mark.asyncio
    async def test_exact_match_en(self) -> None:
        client = DndSu2024Client()
        index_soup = _load("dnd_su24_index.html")
        spell_soup = _load("dnd_su24_hunters_mark.html")

        with patch.object(
            client, "_fetch", new_callable=AsyncMock, side_effect=[index_soup, spell_soup]
        ):
            result = await client.search_spell("Hunter's Mark")

        assert isinstance(result, DndSuSpell)
        assert result.name == "Метка охотника"

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        client = DndSu2024Client()
        index_soup = _load("dnd_su24_index.html")

        with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=index_soup):
            result = await client.search_spell("xyznonexistent")

        assert result is None
