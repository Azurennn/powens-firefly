import logging
import os
import sys
import threading
from contextlib import contextmanager
from logging import LogRecord
from time import sleep
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    from firefly.types.transaction_create_params import Transaction as FireflyTransaction

    from powens_firefly.arguments import Args


logger = logging.getLogger(__name__)


class Color:
    """ANSI color codes for console output."""

    RESET = "\033[0m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    BOLD = "\033[1m"

    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"


class ConsoleManager(logging.Handler):
    """An animated console printer/manager that handles:
    - Animated loading dots (4x2 pattern)
    - Colored log messages above the dots
    - Thread-safe printing
    - Custom object printing with arrows.
    """

    DEPOSIT_ICON = f"{Color.GREEN}→{Color.RESET}"
    WITHDRAWAL_ICON = f"{Color.RED}←{Color.RESET}"
    TRANSFER_ICON = f"{Color.BRIGHT_BLUE}↔{Color.RESET}"

    FAILED_ICON = f"{Color.BOLD}{Color.BRIGHT_RED}✗{Color.RESET} "

    PRINTED_TRANSACTION_PROPERTIES = (
        "description",
        "amount",
        "date",
        "process_date",
        "source_id",
        "destination_id",
    )


    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._animation_active = False
        self._animation_thread: threading.Thread | None = None
        self._stop_animation = threading.Event()
        self.current_message = ""
        self._logs: list[str] = []
        self._animation_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._frame_index = 0

    @staticmethod
    def hide_cursor() -> None:
        sys.stdout.write(Color.HIDE_CURSOR)
        sys.stdout.flush()

    @staticmethod
    def show_cursor() -> None:
        sys.stdout.write(Color.SHOW_CURSOR)
        sys.stdout.flush()

    @staticmethod
    def _clear_line() -> None:
        """Clear the current line and move cursor to start."""
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def print_logs(self) -> None:
        """Print all stored logs and empty storage."""
        for log in self._logs:  # Show last 5 logs
            sys.stdout.write(f"{log}\n")
        self._logs = []

    def _animate_dots(self) -> None:
        """Animation loop for loading dots."""
        while not self._stop_animation.is_set():
            with self._lock:
                if self._animation_active:
                    dots = self._animation_frames[self._frame_index % len(self._animation_frames)]
                    self._clear_line()

                    self.print_logs()

                    # Print animation line
                    sys.stdout.write(f"{dots} {self.current_message}")
                    sys.stdout.flush()
                    self._frame_index += 1
            sleep(0.1)

    def start_animation(self, message: str = "") -> None:
        """Start the loading animation with a message."""
        with self._lock:
            self.current_message = message
            self._animation_active = True
            self._stop_animation.clear()
            if self._animation_thread is None or not self._animation_thread.is_alive():
                self._animation_thread = threading.Thread(target=self._animate_dots, daemon=True)
                self._animation_thread.start()

    def set_animation_message(self, message: str = "") -> None:
        with self._lock:
            self.current_message = message

    def stop_animation(self, final_message: str = "", no_new_line: bool = False) -> None:
        """Stop the loading animation and optionally print a final message."""
        with self._lock:
            self._animation_active = False
            self._stop_animation.set()
            self._clear_line()
            self.print_logs()
            line_end = "\n" if not no_new_line else ""
            if final_message:
                sys.stdout.write(f"{final_message}{line_end}")
            else:
                sys.stdout.write(f"{self.current_message}{line_end}")
            sys.stdout.flush()

    def emit(self, record: LogRecord) -> None:
        """Forward a standard logging record to the ConsoleManager."""
        with self._lock:
            if self._animation_active:
                self._logs.append(self.format(record))
            else:
                sys.stdout.write(f"{self.format(record)}\n")

    @contextmanager
    def animate(self, message: str = "", end_message: str = "", no_new_line: bool = False) -> Generator[ConsoleManager]:
        """"""
        self.start_animation(message=message)
        yield self
        self.stop_animation(final_message=end_message, no_new_line=no_new_line)

    @classmethod
    def get_printing_transaction_parts(
            cls,
            transaction: FireflyTransaction,
    ) -> list[str]:
        parts = []
        for p in cls.PRINTED_TRANSACTION_PROPERTIES:
            if p in transaction:
                property_value = transaction[p]
                if property_value is not None:
                    parts.append(f"{p}: {property_value}")
        return parts


    @classmethod
    def print_deposit(
            cls,
            transaction: FireflyTransaction,
            failed: bool = False,
    ) -> None:
        """
        Print a deposit.
        """
        failed_str = " " if not failed else cls.FAILED_ICON
        symbol = f"{Color.GREEN}→{Color.RESET}"
        parts = cls.get_printing_transaction_parts(transaction=transaction)
        print(f"{failed_str}{symbol} {', '.join(parts)}")

    @classmethod
    def print_withdrawal(
            cls,
            transaction: FireflyTransaction,
            failed: bool = False,
    ) -> None:
        """
        Print a withdrawal.
        """
        failed_str = " " if not failed else cls.FAILED_ICON
        symbol = f"{Color.RED}←{Color.RESET}"
        parts = cls.get_printing_transaction_parts(transaction=transaction)
        print(f"{failed_str}{symbol} {', '.join(parts)}")

    @classmethod
    def print_transfer(
            cls,
            transaction: FireflyTransaction,
            failed: bool = False,
    ):
        """
        Print a transfer.
        """
        failed_str = " " if not failed else cls.FAILED_ICON
        symbol = f"{Color.BRIGHT_BLUE}↔{Color.RESET}"
        parts = cls.get_printing_transaction_parts(transaction=transaction)
        print(f"{failed_str}{symbol} {", ".join(parts)}")

    @classmethod
    def print_all_transactions(
            cls,
            transactions: list[FireflyTransaction],
            failed: bool = False,
    ) -> None:
        """Print all transactions."""
        for t in transactions:
            if t["type"] == "transfer":
                cls.print_transfer(t, failed=failed)
            elif t["type"] == "deposit":
                cls.print_deposit(t, failed=failed)
            elif t["type"] == "withdrawal":
                cls.print_withdrawal(t, failed=failed)
            else:
                logger.error(f"Unknown Firefly III transaction type '{t['type']}'")

    @classmethod
    def args_summary(cls, args: Args) -> str:
        """Print a summary of what arguments were given including dates."""
        auto = ", in automatic mode (--auto)" if args.auto else ""
        dry = ", with no upload (--dry)" if args.dry else ""
        from_date = args.from_date.strftime(
            ", from %-d %B %Y at %H:%M:%S %f UTC%z (--from-date)") if args.from_date is not None else ""
        to_date = args.to_date.strftime(
            ", to %-d %B %Y at %H:%M:%S %f UTC%z (--to-date)") if args.to_date is not None else ""
        no_transfer = "with transfers disabled" if args.no_transfers else ""
        return (
            f"Running powens-firefly with '{args.credentials_path}'" +
            auto +
            dry +
            from_date +
            to_date +
            no_transfer
        )

    @classmethod
    def transactions_summary(
            cls,
            n_deposits: int,
            n_withdrawals: int,
            n_transfers: int,
    ) -> str:
        """Print a summary count of each type of transaction (deposits, withdrawals, transfers)."""
        return (
            f"{cls.DEPOSIT_ICON} {n_deposits} deposit{'' if n_deposits == 1 else 's'}, "
            f"{cls.WITHDRAWAL_ICON} {n_withdrawals} withdrawal{'' if n_withdrawals == 1 else 's'} and "
            f"{cls.TRANSFER_ICON} {n_transfers} transfer{'' if n_transfers == 1 else 's'}"
        )

    @staticmethod
    def demo_sleep(time: float) -> None:
        """Sleep when in demo mode."""
        if "DEMO_MODE" in os.environ:
            sleep(time)
