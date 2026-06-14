"""
Upload methods to firefly-III
"""

import firefly_iii_client
from firefly_iii_client.configuration import Configuration
from firefly_iii_client.models.transaction_split_store import TransactionSplitStore


def upload_transactions(
        firefly_configuration: Configuration,
        transactions: list[TransactionSplitStore],
):
    print("\nUploading transactions to Firefly-III\n")

    for transaction in transactions:
        print(f"Sending {transaction.description} {transaction.amount} ... ", end="")

        transaction_store = firefly_iii_client.TransactionStore(
            apply_rules=True,
            error_if_duplicate_hash=False,
            transactions=[transaction],
        )

        with firefly_iii_client.ApiClient(firefly_configuration) as api_client:
            api_instance = firefly_iii_client.TransactionsApi(api_client)
            api_response = api_instance.store_transaction(transaction_store)

        print("sent")
