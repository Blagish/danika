from enum import StrEnum

from discord import Locale
from discord.app_commands import TranslationContext, Translator, locale_str

_RU = Locale.russian

# -- general ------------------------------------------------------------------
CMD_PING = locale_str("Check bot latency")
CMD_HELP = locale_str("Show available commands")
ARG_HELP_COMMAND = locale_str("Command name for detailed help")

# -- dice ---------------------------------------------------------------------
CMD_ROLL = locale_str(r"Roll dice. Example: d20+3, 2*(d6+1)")
ARG_ROLL_EXPRESSION = locale_str("Dice expression, e.g.: d20+3, 2d6, 3*(d8+2)")

# -- dnd5e --------------------------------------------------------------------
CMD_DND_SPELL = locale_str("Find a D&D 5e spell")
ARG_SPELL_NAME = locale_str("Spell name")
ARG_SOURCE_LANG = locale_str("Source language")
ARG_EDITION = locale_str("Rules edition")

# -- pf2 ----------------------------------------------------------------------
CMD_PF2_SPELL = locale_str("Find a Pathfinder 2e spell")
ARG_PF2_SPELL_NAME = locale_str("Spell name (in English)")


class Section(StrEnum):
    """Секции /help — значения совпадают с name= когов."""

    DICE = "Dice"
    LOOKUP = "Lookup"
    GENERAL = "General"


# Порядок секций в /help
HELP_SECTION_ORDER: list[Section] = [Section.DICE, Section.LOOKUP, Section.GENERAL]

# Единый словарь переводов.
# Ключи slash-команд — сами английские строки (из locale_str.message), "en" не нужен.
# Ключи UI-строк — dot-notation, "en" обязателен.
_TRANSLATIONS: dict[str, dict[str, str]] = {
    # -- slash commands -------------------------------------------------------
    CMD_PING.message: {"ru": "Проверить задержку бота"},
    CMD_HELP.message: {"ru": "Показать доступные команды"},
    ARG_HELP_COMMAND.message: {"ru": "Название команды для подробной справки"},
    CMD_ROLL.message: {"ru": r"Бросить кубы. Пример: д20+3, 2*(д6+1)"},
    ARG_ROLL_EXPRESSION.message: {"ru": "Выражение броска, например: д20+3, 2д6, 3*(d8+2)"},
    CMD_DND_SPELL.message: {"ru": "Найти заклинание D&D 5e"},
    ARG_SPELL_NAME.message: {"ru": "Название заклинания"},
    ARG_SOURCE_LANG.message: {"ru": "Язык источника"},
    ARG_EDITION.message: {"ru": "Редакция правил"},
    CMD_PF2_SPELL.message: {"ru": "Найти заклинание Pathfinder 2e"},
    ARG_PF2_SPELL_NAME.message: {"ru": "Название заклинания (на английском)"},
    # -- UI embed strings -----------------------------------------------------
    "help.title": {"en": "Danika — help", "ru": "Danika — помощь"},
    f"help.section.{Section.DICE}": {"en": Section.DICE, "ru": "Кубы"},
    f"help.section.{Section.LOOKUP}": {"en": Section.LOOKUP, "ru": "Поиск"},
    f"help.section.{Section.GENERAL}": {"en": Section.GENERAL, "ru": "Общее"},
    "help.roll.title": {"en": "/roll — syntax", "ru": "/roll — синтаксис"},
    "help.roll.hint": {
        "en": "\n-# details: `/help command:roll`",
        "ru": "\n-# подробнее: `/help command:roll`",
    },
    "help.examples": {"en": "Examples", "ru": "Примеры"},
    "help.parameters": {"en": "Parameters", "ru": "Параметры"},
    "help.optional": {"en": "*(optional)*", "ru": "*(необязательно)*"},
    "help.not_found": {"en": "Command not found.", "ru": "Команда не найдена."},
    "roll.syntax": {
        "en": (
            "```\n"
            "d20          — roll a d20\n"
            "3d6          — roll 3d6, sum\n"
            "ad20 / dd20  — advantage / disadvantage\n"
            "4d6p3        — roll 4d6, keep 3 best\n"
            "+ - * / //   — arithmetic\n"
            "2*(d6+1)     — parentheses\n"
            "d20+5, 2d6   — multiple rolls\n"
            "```"
        ),
        "ru": (
            "```\n"
            "d20          — бросить d20\n"
            "3d6          — бросить 3d6, сумма\n"
            "ad20 / dd20  — преимущество / помеха\n"
            "4d6p3        — бросить 4d6, взять 3 лучших\n"
            "+ - * / //   — арифметика\n"
            "2*(d6+1)     — скобки\n"
            "d20+5, 2d6   — несколько бросков\n"
            "Кириллица: д, ад, дд, п\n"
            "```"
        ),
    },
}


def t(key: str, locale: Locale) -> str:
    """Возвращает UI-строку для указанной локали.

    Attributes:
        key: Ключ строки из _TRANSLATIONS.
        locale: Локаль пользователя.
    """
    lang = "ru" if locale is _RU else "en"
    entry = _TRANSLATIONS.get(key, {})
    return entry.get(lang) or entry.get("en") or key


class DanikaTranslator(Translator):
    async def translate(
        self, string: locale_str, locale: Locale, context: TranslationContext
    ) -> str | None:
        """Переводит строку на запрошенную локаль.

        Attributes:
            string: Переводимая строка.
            locale: Целевая локаль.
            context: Контекст перевода (команда, параметр и т.п.).
        """
        lang = "ru" if locale is _RU else "en"
        return _TRANSLATIONS.get(string.message, {}).get(lang)
