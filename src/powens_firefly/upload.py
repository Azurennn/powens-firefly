"""Upload methods to firefly-III."""
from typing import TYPE_CHECKING

import firefly_iii_client

if TYPE_CHECKING:
    from firefly_iii_client.configuration import Configuration
    from firefly_iii_client.models.transaction_split_store import TransactionSplitStore

    from powens_firefly.console import ConsoleManager, Color


def upload_transactions(
        firefly_configuration: Configuration,
        transactions: list[TransactionSplitStore],
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

            transaction_store = firefly_iii_client.TransactionStore(
                apply_rules=True,
                error_if_duplicate_hash=False,
                transactions=[transaction],
            )

            try:
                with firefly_iii_client.ApiClient(firefly_configuration) as api_client:
                    api_instance = firefly_iii_client.TransactionsApi(api_client)
                    api_response = api_instance.store_transaction(transaction_store)
            except:
                failed_transactions.append(transaction)

            printer.demo_sleep(0.005)

        printer.set_animation_message("")


    if failed_transactions:
        print(f"{Color.BRIGHT_RED}\n{len(failed_transactions)} transaction{'s' if len(failed_transactions) > 1 else ''} "
              f"failed to upload.{Color.RESET}")
        printer.print_all_transactions(failed_transactions, failed=True)
