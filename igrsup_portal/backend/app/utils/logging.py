import sys

from loguru import logger


def configure_logging(log_level: str) -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=False,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        level=log_level.upper(),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    )


__all__ = ["logger", "configure_logging"]
