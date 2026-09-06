"""Logger configuration module."""
import logging.config
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from powens_firefly.cli import Args
    from powens_firefly.console import ConsoleManager


def configure_logger(args: Args, printer: ConsoleManager) -> None:
    """Configure the runtime logging configuration."""
    if args.quiet:
        level = logging.ERROR
    elif args.verbose:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console_manager": {
                "()": lambda: printer,
                "formatter": "standard",
            },
        },
        "root": {
            "handlers": ["console_manager"],
            "level": level,
        },
    })
