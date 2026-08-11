import logging
import sys
import time
import threading
from collections.abc import Generator
from contextlib import contextmanager
from logging import LogRecord

from firefly_iii_client import TransactionSplitStore, TransactionTypeProperty

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
    """
    An animated console printer/manager that handles:
    - Animated loading dots (4x2 pattern)
    - Colored log messages above the dots
    - Thread-safe printing
    - Custom object printing with arrows
    """

    def __init__(self):
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
    def _clear_line():
        """Clear the current line and move cursor to start."""
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def print_logs(self) -> None:
        """Print all stored logs and empty storage."""
        for log in self._logs:  # Show last 5 logs
            sys.stdout.write(f"{log}\n")
        self._logs = []

    def _animate_dots(self):
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
            time.sleep(0.1)

    def start_animation(self, message: str = ""):
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

    def stop_animation(self, final_message: str = "", no_new_line: bool = False):
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
    def animate(self, message: str = "", end_message: str = "", no_new_line: bool = False) -> Generator[ConsoleManager, None, None]:
        """"""
        self.start_animation(message=message)
        yield self
        self.stop_animation(final_message=end_message, no_new_line=no_new_line)

    printed_transaction_properties = (
        "description",
        "amount",
        "date",
        "process_date",
        "source_id",
        "destination_id",
    )

    @classmethod
    def get_printing_transaction_parts(
            cls,
            transaction: TransactionSplitStore,
    ) -> list[str]:
        parts = []
        for p in cls.printed_transaction_properties:
            if hasattr(transaction, p):
                property_value = getattr(transaction, p)
                if property_value is not None:
                    parts.append(f"{p}: {property_value}")
        return parts

    failed_str = f"{Color.BOLD}{Color.BRIGHT_RED}✗{Color.RESET} "

    @classmethod
    def print_deposit(
            cls,
            transaction: TransactionSplitStore,
            failed: bool = False,
    ) -> None:
        """
        Print a deposit.
        """
        failed_str = " " if not failed else cls.failed_str
        symbol = f"{Color.GREEN}→{Color.RESET}"
        parts = cls.get_printing_transaction_parts(transaction=transaction)
        print(f"{failed_str}{symbol} {', '.join(parts)}")

    @classmethod
    def print_withdrawal(
            cls,
            transaction: TransactionSplitStore,
            failed: bool = False,
    ) -> None:
        """
        Print a withdrawal.
        """
        failed_str = " " if not failed else cls.failed_str
        symbol = f"{Color.RED}←{Color.RESET}"
        parts = cls.get_printing_transaction_parts(transaction=transaction)
        print(f"{failed_str}{symbol} {', '.join(parts)}")

    @classmethod
    def print_transfer(
            cls,
            transaction: TransactionSplitStore,
            failed: bool = False,
    ):
        """
        Print a transfer.
        """
        failed_str = " " if not failed else cls.failed_str
        symbol = f"{Color.BRIGHT_BLUE}↔{Color.RESET}"
        parts = cls.get_printing_transaction_parts(transaction=transaction)
        print(f"{failed_str}{symbol} {", ".join(parts)}")

    @classmethod
    def print_all_transactions(
            cls,
            transactions: list[TransactionSplitStore],
            failed: bool = False,
    ) -> None:
        """Print all transactions."""
        for t in transactions:
            if t.type == TransactionTypeProperty.TRANSFER:
                cls.print_transfer(t, failed=failed)
            elif t.type == TransactionTypeProperty.DEPOSIT:
                cls.print_deposit(t, failed=failed)
            elif t.type == TransactionTypeProperty.WITHDRAWAL:
                cls.print_withdrawal(t, failed=failed)
            else:
                logger.error(f"Unknown Firefly III transaction type '{t.type}'")
