import sys

from loguru import logger

from app.config import get_config


def _log_format(record: dict) -> str:
    """Формат лога — базовый + extra-поля если есть."""
    extra = record["extra"]
    module = extra.get("module", record["name"])
    base = (
        f"<green>{{time:YYYY-MM-DD HH:mm:ss}}</green>"
        f" | <level>{{level: <8}}</level>"
        f" | <cyan>{module}</cyan>"
        f" | <level>{{message}}</level>"
    )
    context = {k: v for k, v in extra.items() if k != "module"}
    if context:
        pairs = " ".join(f"{k}={v!r}" for k, v in context.items())
        base += f" | {pairs}"
    return base + "\n{exception}"


def setup_logging() -> None:
    """Настраивает loguru: убирает дефолтный синк, добавляет stderr с кастомным форматом."""
    config = get_config()
    logger.remove()
    level = "DEBUG" if config.run_mode == "dev" else "INFO"
    logger.add(sys.stderr, level=level, format=_log_format)
