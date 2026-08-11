"""
Logger configuration module.
"""
import logging.config
from typing import TYPE_CHECKING

from powens_firefly.console import ConsoleManager

if TYPE_CHECKING:
    from powens_firefly.cli import Args


def configure_logger(args: Args, printer: ConsoleManager):
    """
    Configure the runtime logging configuration.
    """
    if args.quiet:
        level = logging.ERROR
    elif args.verbose:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(levelname)s %(message)s",
    )

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
