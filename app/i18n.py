from discord import Locale
from discord.app_commands import TranslationContext, Translator, locale_str

_RU = Locale.russian

# -- general ------------------------------------------------------------------
CMD_PING = locale_str("Check bot latency")

# -- dice ---------------------------------------------------------------------
CMD_ROLL = locale_str("Roll dice. Example: d20+3, 2*(d6+1)")
ARG_ROLL_EXPRESSION = locale_str("Dice expression, e.g.: d20+3, 2d6, 3*(d8+2)")

# -- dnd5e --------------------------------------------------------------------
CMD_DND_SPELL = locale_str("Find a D&D 5e spell")
ARG_SPELL_NAME = locale_str("Spell name")
ARG_SOURCE_LANG = locale_str("Source language")
ARG_EDITION = locale_str("Rules edition")

# -- pf2 ----------------------------------------------------------------------
CMD_PF2_SPELL = locale_str("Find a Pathfinder 2e spell")
ARG_PF2_SPELL_NAME = locale_str("Spell name (in English)")

_T: dict[str, dict[Locale, str]] = {
    CMD_PING.message: {_RU: "Проверить задержку бота"},
    CMD_ROLL.message: {_RU: "Бросить кубы. Пример: д20+3, 2*(д6+1)"},
    ARG_ROLL_EXPRESSION.message: {_RU: "Выражение броска, например: д20+3, 2д6, 3*(d8+2)"},
    CMD_DND_SPELL.message: {_RU: "Найти заклинание D&D 5e"},
    ARG_SPELL_NAME.message: {_RU: "Название заклинания"},
    ARG_SOURCE_LANG.message: {_RU: "Язык источника"},
    ARG_EDITION.message: {_RU: "Редакция правил"},
    CMD_PF2_SPELL.message: {_RU: "Найти заклинание Pathfinder 2e"},
    ARG_PF2_SPELL_NAME.message: {_RU: "Название заклинания (на английском)"},
}


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
        return _T.get(string.message, {}).get(locale)
