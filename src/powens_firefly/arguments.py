"""Command line arguments for powens-firefly."""
import argparse
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


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
    from_date: datetime | None
    to_date: datetime | None
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
        help="Path to the credentials yaml file. (default = 'credentials.yml')",
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
        "--from-date",
        type=parse_date,
        help="Initial date for transactions. Limits the start of transactions in chronological order.",
    )

    parser.add_argument(
        "--to-date",
        type=parse_date,
        help="Final date for transactions. Limits the end of transactions in chronological order.",
    )

    parser.add_argument(
        "--transaction-limit",
        type=int,
        default=1000,
        help="Limit for all transactions fetched. (default = 1000)",
    )

    parser.add_argument(
        "--no-transfers",
        action="store_true",
        help="Disable the combining of transactions into transfers considered to be the same between bank accounts.",
    )

    return parser
