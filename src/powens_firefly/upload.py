"""Upload methods to firefly-III."""
from typing import TYPE_CHECKING

# import random  # noqa: ERA001

if TYPE_CHECKING:
    from firefly import Firefly
    from firefly.types.transaction_create_params import Transaction as FireflyTransaction

    from powens_firefly.console import ConsoleManager


DESCRIPTION_DISPLAY_CHAR_LIMIT = 20


def upload_transactions(
        firefly_client: Firefly,
        transactions: list[FireflyTransaction],
        printer: ConsoleManager,
) -> None:
    """
    Upload transactions to firefly-III.

    Displays a loading screen and a status of uploaded transactions once finished.
    """
    with printer.animate(message="Uploading transactions", no_new_line=True):

        total_t = len(transactions)
        failed_transactions = []
        for index, transaction in enumerate(transactions):

            printer.set_animation_message(
                f"Uploading transactions {(index + 1) / total_t * 100:.0f}% "
                # f"{'x' * random.randrange(3, 18)}",  # noqa: ERA001
                f"{d if len(d := transaction["description"]) < DESCRIPTION_DISPLAY_CHAR_LIMIT
                else d[:DESCRIPTION_DISPLAY_CHAR_LIMIT - 2] + "..."}",
            )

            try:
                firefly_client.transactions.create(
                    transactions=[transaction],
                    apply_rules=True,
                    error_if_duplicate_hash=False,
                )
            except:
                failed_transactions.append(transaction)

            printer.demo_sleep(0.005)

        printer.set_animation_message()

    success_pct = (1 - (len(failed_transactions) / total_t) )* 100
    print(f"Successfully uploaded {success_pct:.0f}% of transactions")

    if failed_transactions:
        from powens_firefly.console import Color
        print(f"{Color.BRIGHT_RED}\n{len(failed_transactions)} "
              f"transaction{'s' if len(failed_transactions) > 1 else ''} failed to upload.{Color.RESET}")
        printer.print_all_transactions(failed_transactions, failed=True)
