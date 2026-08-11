"""
Client endpoint for powens-firefly.
"""
import argparse
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def main(input_args=None):
    args = build_parser().parse_args(input_args, namespace=Args())
    from powens_firefly.logger import configure_logger
    from powens_firefly.console import ConsoleManager, Color
    printer = ConsoleManager()

    if args.version:
        from importlib.metadata import version
        __version__ = version("powens-firefly")
        print(f"\n {Color.BOLD}powens-firefly {Color.BRIGHT_BLUE}{__version__}{Color.RESET}\n")
        return

    try:
        configure_logger(args, printer)
        from powens_firefly.app import run
        from asyncio import run as arun
        arun(run(args, printer))

    except KeyboardInterrupt:
        from powens_firefly.console import Color
        print(f"\n{Color.BOLD}powens-firefly stopped.", flush=True)

    finally:
        printer.show_cursor()


def parse_date(value: str) -> datetime:
    from dateutil.parser import parse
    return parse(value)


class Args:
    verbose: bool
    quiet: bool
    version: bool
    credentials_path: Path
    auto: bool
    dry: bool
    min_date: datetime
    max_date: datetime
    transaction_limit: int
    no_transfers: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-v", "-V", "--verbose",
        action="store_true",
        help="Verbose mode, more information is written in the console.",
    )

    parser.add_argument(
        "-q", "-Q", "--quiet",
        action="store_true",
        help="quiet mode, less information is written in the console.",
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Only show powens-firefly version.",
    )

    parser.add_argument(
        "--credentials-path",
        type=Path,
        default=Path("credentials.yml"),
        help="Path to the credentials yaml file.",
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatic mode, "
             "script fails if action required by user, ie redo any authentication.",
    )

    parser.add_argument(
        "--dry",
        action="store_true",
        help="Dry run mode, "
             "Script runs normaly but skips the upload phase to Firefly-III.",
    )

    parser.add_argument(
        "--min-date",
        type=parse_date,
        help="Minimum date for transactions.",
    )

    parser.add_argument(
        "--max-date",
        type=parse_date,
        help="Maximum date for transactions.",
    )

    parser.add_argument(
        "--transaction-limit",
        type=int,
        default=1000,
        help="Limit for all transactions fetched (default = 1000)",
    )

    parser.add_argument(
        "--no-transfers",
        action="store_true",
        help="Disable the combining of transactions into transfers considered to be the same between bank accounts.",
    )

    return parser
