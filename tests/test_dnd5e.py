from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from bs4 import BeautifulSoup

from app.systems.dnd5e_wikidot import Dnd5eWikidotClient, Dnd5eWikidotSpell, Dnd2024WikidotClient
from app.systems.types import SpellMatch

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> BeautifulSoup:
    return BeautifulSoup((FIXTURES / name).read_text(), "html.parser")


# ---------------------------------------------------------------------------
# _parse_spell_page — парсинг замороженных HTML-страниц
# ---------------------------------------------------------------------------


class TestParseSpellPage:
    """Тесты парсинга HTML-страницы заклинания."""

    client = Dnd5eWikidotClient()

    def test_fireball_basics(self) -> None:
        soup = _load("wikidot_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd5e.wikidot.com/spell:fireball")

        assert isinstance(spell, Dnd5eWikidotSpell)
        assert spell.name == "Fireball"
        assert spell.level == 3
        assert spell.school == "Evocation"
        assert spell.ritual is False
        assert spell.concentration is False

    def test_fireball_stats(self) -> None:
        soup = _load("wikidot_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd5e.wikidot.com/spell:fireball")

        assert spell.casting_time == "1 action"
        assert spell.range == "150 feet"
        assert "bat guano" in spell.components
        assert spell.duration == "Instantaneous"

    def test_fireball_higher_levels(self) -> None:
        soup = _load("wikidot_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd5e.wikidot.com/spell:fireball")

        assert spell.higher_levels is not None
        assert "1d6" in spell.higher_levels

    def test_fireball_classes(self) -> None:
        soup = _load("wikidot_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd5e.wikidot.com/spell:fireball")

        assert "Sorcerer" in spell.classes
        assert "Wizard" in spell.classes

    def test_fireball_source(self) -> None:
        soup = _load("wikidot_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd5e.wikidot.com/spell:fireball")

        assert spell.source is not None
        assert "Player's Handbook" in spell.source

    def test_fireball_description(self) -> None:
        soup = _load("wikidot_fireball.html")
        spell = self.client._parse_spell_page(soup, "https://dnd5e.wikidot.com/spell:fireball")

        assert "8d6 fire damage" in spell.description

    def test_cantrip_mending(self) -> None:
        soup = _load("wikidot_mending.html")
        spell = self.client._parse_spell_page(soup, "https://dnd5e.wikidot.com/spell:mending")

        assert spell.name == "Mending"
        assert spell.level == 0
        assert spell.school == "Transmutation"
        assert spell.casting_time == "1 minute"
        assert spell.higher_levels is None

    def test_ritual_detect_magic(self) -> None:
        soup = _load("wikidot_detect_magic.html")
        spell = self.client._parse_spell_page(
            soup, "https://dnd5e.wikidot.com/spell:detect-magic"
        )

        assert spell.name == "Detect Magic"
        assert spell.level == 1
        assert spell.school == "Divination"
        assert spell.ritual is True
        assert spell.concentration is True
        assert "Concentration" in spell.duration

    def test_url_passthrough(self) -> None:
        soup = _load("wikidot_fireball.html")
        url = "https://dnd5e.wikidot.com/spell:fireball"
        spell = self.client._parse_spell_page(soup, url)

        assert spell.url == url


# ---------------------------------------------------------------------------
# Nathair's Mischief — интеграция встроенной таблицы в описание
# ---------------------------------------------------------------------------


class TestNathairsMischief:
    """Проверка поддержки <table> внутри описания заклинания."""

    client = Dnd5eWikidotClient()

    def _spell(self) -> Dnd5eWikidotSpell:
        soup = _load("wikidot_nathairs_mischief.html")
        return self.client._parse_spell_page(
            soup, "https://dnd5e.wikidot.com/spell:nathairs-mischief"
        )

    def test_table_title_in_description(self) -> None:
        spell = self._spell()
        assert "Mischievous Surge" in spell.description

    def test_row_effect_text_in_description(self) -> None:
        spell = self._spell()
        assert "apple pie" in spell.description

    def test_table_follows_narrative_paragraph(self) -> None:
        spell = self._spell()
        desc = spell.description
        narrative_idx = desc.find("Roll on the Mischievous Surge")
        table_idx = desc.find("**Mischievous Surge**")
        assert narrative_idx != -1
        assert table_idx != -1
        assert narrative_idx < table_idx

    def test_all_four_rows_rendered(self) -> None:
        spell = self._spell()
        # Все четыре строки d4: проверим по характерным словам из эффектов.
        for marker in ("apple pie", "flowers", "giggling", "molasses"):
            assert marker in spell.description


# ---------------------------------------------------------------------------
# _parse_level_school
# ---------------------------------------------------------------------------


class TestParseLevelSchool:
    """Тесты разбора строки уровня и школы магии."""

    parse = staticmethod(Dnd5eWikidotClient._parse_level_school)

    def test_cantrip(self) -> None:
        assert self.parse("Transmutation cantrip") == (0, "Transmutation", False)

    def test_numbered_level(self) -> None:
        assert self.parse("3rd-level evocation") == (3, "Evocation", False)

    def test_ritual(self) -> None:
        level, school, ritual = self.parse("1st-level divination (ritual)")
        assert level == 1
        assert school == "Divination"
        assert ritual is True

    def test_all_ordinals(self) -> None:
        for i, ordinal in enumerate(["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"], 1):
            level, _, _ = self.parse(f"{ordinal}-level abjuration")
            assert level == i


# ---------------------------------------------------------------------------
# search_spell — интеграция с замоканным _fetch
# ---------------------------------------------------------------------------


class TestSearchSpell:
    """Тесты поиска заклинания (HTTP замокан через фикстуры).

    Порядок вызовов _fetch: сначала _fetch_spell_list (полный список),
    затем при единственном совпадении — страница заклинания.
    """

    @pytest.mark.asyncio
    async def test_exact_match(self) -> None:
        client = Dnd5eWikidotClient()
        all_spells_soup = _load("wikidot_spells_all.html")
        spell_soup = _load("wikidot_fireball.html")

        with patch.object(client, "_fetch", new_callable=AsyncMock, side_effect=[all_spells_soup, spell_soup]):
            result = await client.search_spell("fireball")

        assert isinstance(result, Dnd5eWikidotSpell)
        assert result.name == "Fireball"

    @pytest.mark.asyncio
    async def test_fuzzy_match(self) -> None:
        """Опечатка 'fierball' находит Fireball."""
        client = Dnd5eWikidotClient()
        all_spells_soup = _load("wikidot_spells_all.html")
        spell_soup = _load("wikidot_fireball.html")

        with patch.object(client, "_fetch", new_callable=AsyncMock, side_effect=[all_spells_soup, spell_soup]):
            result = await client.search_spell("fierball")

        assert isinstance(result, Dnd5eWikidotSpell)
        assert result.name == "Fireball"

    @pytest.mark.asyncio
    async def test_disambiguation(self) -> None:
        client = Dnd5eWikidotClient()
        all_spells_soup = _load("wikidot_spells_all.html")

        with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=all_spells_soup):
            result = await client.search_spell("fire")

        assert isinstance(result, list)
        assert all(isinstance(m, SpellMatch) for m in result)
        assert len(result) > 1

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        client = Dnd5eWikidotClient()
        all_spells_soup = _load("wikidot_spells_all.html")

        with patch.object(client, "_fetch", new_callable=AsyncMock, return_value=all_spells_soup):
            result = await client.search_spell("xyznonexistent")

        assert result is None


# ===========================================================================
# Dnd2024WikidotClient
# ===========================================================================


class TestParseLevelSchool2024:
    """Разбор строки уровня/школы/классов формата 2024."""

    parse = staticmethod(Dnd2024WikidotClient._parse_level_school_2024)

    def test_leveled(self) -> None:
        level, school, classes = self.parse("Level 3 Evocation (Sorcerer, Wizard)")
        assert level == 3
        assert school == "Evocation"
        assert classes == ["Sorcerer", "Wizard"]

    def test_cantrip(self) -> None:
        level, school, classes = self.parse("Evocation Cantrip (Artificer, Sorcerer, Wizard)")
        assert level == 0
        assert school == "Evocation"
        assert "Artificer" in classes

    def test_no_classes(self) -> None:
        level, school, classes = self.parse("Level 5 Conjuration")
        assert level == 5
        assert school == "Conjuration"
        assert classes == []


class TestParseSpellPage2024:
    """Парсинг HTML-страниц заклинаний с dnd2024.wikidot.com."""

    client = Dnd2024WikidotClient()

    def test_fireball_basics(self) -> None:
        soup = _load("wikidot2024_fireball.html")
        spell = self.client._parse_spell_page(soup, "http://dnd2024.wikidot.com/spell:fireball")

        assert isinstance(spell, Dnd5eWikidotSpell)
        assert spell.name == "Fireball"
        assert spell.level == 3
        assert spell.school == "Evocation"
        assert spell.ritual is False
        assert spell.concentration is False

    def test_fireball_classes_from_level_line(self) -> None:
        soup = _load("wikidot2024_fireball.html")
        spell = self.client._parse_spell_page(soup, "http://dnd2024.wikidot.com/spell:fireball")

        assert "Sorcerer" in spell.classes
        assert "Wizard" in spell.classes

    def test_fireball_stats(self) -> None:
        soup = _load("wikidot2024_fireball.html")
        spell = self.client._parse_spell_page(soup, "http://dnd2024.wikidot.com/spell:fireball")

        assert spell.casting_time == "Action"
        assert spell.range == "150 feet"
        assert "bat guano" in spell.components
        assert spell.duration == "Instantaneous"

    def test_fireball_higher_levels(self) -> None:
        soup = _load("wikidot2024_fireball.html")
        spell = self.client._parse_spell_page(soup, "http://dnd2024.wikidot.com/spell:fireball")

        assert spell.higher_levels is not None
        assert "1d6" in spell.higher_levels

    def test_fireball_source(self) -> None:
        soup = _load("wikidot2024_fireball.html")
        spell = self.client._parse_spell_page(soup, "http://dnd2024.wikidot.com/spell:fireball")

        assert spell.source == "Player's Handbook"

    def test_cantrip_fire_bolt(self) -> None:
        soup = _load("wikidot2024_fire_bolt.html")
        spell = self.client._parse_spell_page(soup, "http://dnd2024.wikidot.com/spell:fire-bolt")

        assert spell.name == "Fire Bolt"
        assert spell.level == 0
        assert spell.school == "Evocation"
        assert "Artificer" in spell.classes
        assert spell.higher_levels is not None
        assert "1d10" in spell.higher_levels

    def test_ritual_detect_magic(self) -> None:
        soup = _load("wikidot2024_detect_magic.html")
        spell = self.client._parse_spell_page(
            soup, "http://dnd2024.wikidot.com/spell:detect-magic"
        )

        assert spell.name == "Detect Magic"
        assert spell.level == 1
        assert spell.school == "Divination"
        assert spell.ritual is True
        assert spell.concentration is True
        assert "Ritual" in spell.casting_time

    def test_fireball_description(self) -> None:
        soup = _load("wikidot2024_fireball.html")
        spell = self.client._parse_spell_page(soup, "http://dnd2024.wikidot.com/spell:fireball")

        assert "8d6 Fire damage" in spell.description


class TestSearchSpell2024:
    """Тесты поиска заклинания на dnd2024.wikidot.com."""

    @pytest.mark.asyncio
    async def test_exact_match(self) -> None:
        client = Dnd2024WikidotClient()
        all_spells_soup = _load("wikidot2024_spells_all.html")
        spell_soup = _load("wikidot2024_fireball.html")

        with patch.object(
            client, "_fetch", new_callable=AsyncMock, side_effect=[all_spells_soup, spell_soup]
        ):
            result = await client.search_spell("fireball")

        assert isinstance(result, Dnd5eWikidotSpell)
        assert result.name == "Fireball"

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        client = Dnd2024WikidotClient()
        all_spells_soup = _load("wikidot2024_spells_all.html")

        with patch.object(
            client, "_fetch", new_callable=AsyncMock, return_value=all_spells_soup
        ):
            result = await client.search_spell("xyznonexistent")

        assert result is None
