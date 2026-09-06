"""Upload methods to firefly-III."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from powens_firefly.console import ConsoleManager, Color
    from firefly import Firefly
    from firefly.types.transaction_create_params import Transaction as FireflyTransaction


def upload_transactions(
        firefly_client: Firefly,
        transactions: list[FireflyTransaction],
        printer: ConsoleManager,
) -> None:
    with printer.animate(message="Uploading transactions", no_new_line=True):

        total_t = len(transactions)
        failed_transactions = []
        for index, transaction in enumerate(transactions):

            printer.set_animation_message(
                f"Uploading transactions {(index + 1) / total_t * 100:.0f}% "
                # f"{'x' * random.randrange(3, 18)}",  # noqa:
                f"{transaction.description if len(transaction.description) < 20
                else transaction.description[:18] + "..."}",
            )

            try:
                result = firefly_client.transactions.create(
                    transactions=[transaction],
                    apply_rules=True,
                    error_if_duplicate_hash=False,
                )
            except:
                failed_transactions.append(transaction)

            printer.demo_sleep(0.005)

        printer.set_animation_message("")


    if failed_transactions:
        print(f"{Color.BRIGHT_RED}\n{len(failed_transactions)} transaction{'s' if len(failed_transactions) > 1 else ''} "
              f"failed to upload.{Color.RESET}")
        printer.print_all_transactions(failed_transactions, failed=True)
