"""Client endpoint for powens-firefly."""
import logging

logger = logging.getLogger(__name__)


def main(input_args=None) -> None:
    from powens_firefly.arguments import Args, build_parser
    args = build_parser().parse_args(input_args, namespace=Args())
    from powens_firefly.console import ConsoleManager
    printer = ConsoleManager()

    if args.version:
        from importlib.metadata import version
        __version__ = version("powens-firefly")
        from powens_firefly.console import Color
        print(f" {Color.BOLD}powens-firefly {Color.BRIGHT_BLUE}{__version__}{Color.RESET}\n")
        return

    print(printer.args_summary(args), flush=True)

    from firefly import APIConnectionError as FireflyAPIConnectionError
    from powens import PowensConnectionError

    try:
        from powens_firefly.logger import configure_logger
        configure_logger(args, printer)
        from asyncio import run as arun

        from powens_firefly.app import run
        arun(run(args, printer))

    except KeyboardInterrupt:
        from powens_firefly.console import Color
        print(f"\n{Color.BOLD}powens-firefly stopped.", flush=True)

    except PowensConnectionError:
        from powens_firefly.console import Color
        print(f"\n{Color.BOLD}powens-firefly couldn't connect to Powens.", flush=True)

    except FireflyAPIConnectionError:
        from powens_firefly.console import Color
        print(f"\n{Color.BOLD}powens-firefly couldn't connect to Firefly-III.", flush=True)

    finally:
        printer.show_cursor()
