"""Client endpoint for powens-firefly."""
import logging

from powens_firefly.arguments import Args, build_parser

logger = logging.getLogger(__name__)


def main(input_args=None) -> None:
    args = build_parser().parse_args(input_args, namespace=Args())
    from powens_firefly.console import ConsoleManager
    printer = ConsoleManager()

    if args.version:
        from importlib.metadata import version
        version("powens-firefly")
        return

    try:
        from powens_firefly.logger import configure_logger
        configure_logger(args, printer)
        from asyncio import run as arun
        from powens_firefly.app import run
        arun(run(args, printer))

    except KeyboardInterrupt:
        from powens_firefly.console import Color
        print(f"\n{Color.BOLD}powens-firefly stopped.", flush=True)

    finally:
        printer.show_cursor()
