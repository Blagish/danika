# Danika Debott

Discord-бот для настольных ролевых игр: бросает кубики, поддерживает выражения с собственным DSL.

## Требования

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/) — менеджер пакетов и виртуальных окружений

## Установка

```bash
uv sync
```

Это создаст виртуальное окружение и установит все зависимости (включая dev-группу).

## Настройка

Скопируйте `.env.example` в `.env` (или создайте `.env` вручную) и заполните переменные:

```
DISCORD_TOKEN=...
RUN_MODE=dev
DEV_GUILD_ID=...
```

## Запуск

```bash
uv run main.py
```

## Разработка

Установите pre-commit хуки:

```bash
uv run pre-commit install
```

Хуки автоматически проверяют код при каждом коммите (ruff lint/format, проверка файлов). Чтобы запустить вручную на всех файлах:

```bash
uv run pre-commit run --all-files
```

## Тесты

```bash
# Все тесты
uv run pytest

# Конкретный тест
uv run pytest tests/test_dice.py::test_name

# С выводом print/log
uv run pytest -s
```
