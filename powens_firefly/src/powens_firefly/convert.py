"""
Method to convert all Powens transactions into Firefly transactions
"""
from enum import nonmember
from typing import Any, List
from datetime import datetime as dt
import pandas as pd

from firefly_iii_client.models.autocomplete_account import AutocompleteAccount
from firefly_iii_client.models.transaction_split_store import TransactionSplitStore
from firefly_iii_client.models.transaction_type_property import TransactionTypeProperty

from powens.account import PowensAccount
from powens.transaction import PowensTransactionType, PowensTransaction


class Powens2FireflyAccount:
    powens_account: PowensAccount
    firefly_account: AutocompleteAccount

    powens_transactions: List[PowensTransaction]
    firefly_transactions: List[PowensTransaction] = []

    def __init__(
            self,
            powens_account: PowensAccount,
            firefly: AutocompleteAccount,
            powens_transactions: List[PowensTransaction],
    ):
        self.powens_account = powens_account
        self.firefly_account = firefly
        self.powens_transactions = powens_transactions


class Powens2Firefly:

    mappings: dict[int, int]
    powens2firefly_accounts: list[Powens2FireflyAccount]

    def __init__(
            self,
            mappings: dict[int, int],
            powens2firefly_accounts: list[Powens2FireflyAccount]
    ):
        self.mappings = mappings
        self.powens2firefly_accounts = powens2firefly_accounts

    def get_transactions_transfer_related_account(
            self,
            origin_account: PowensAccount,
            origin_transaction: PowensTransaction,
    ) -> list[PowensTransaction] | None:
        """
        Get all the transactions from the account in relation to the target_transaction
        from another account.
        """
        if (
                origin_transaction.counterparty is None or
                origin_transaction.counterparty.account_identification is None
        ):
            return None

        for account in self.powens2firefly_accounts:
            # Skip the same account
            if origin_account.iban == account.powens_account.iban:
                continue

            # Find the transaction account transferred from/to
            if origin_transaction.counterparty.account_identification == account.powens_account.iban:
                return account.powens_transactions

        return None

    def find_iban_datetime(
            self,
            origin_account: PowensAccount,
            origin_transaction: PowensTransaction,
    ) -> PowensTransaction | None:

        if (
                origin_account.iban is None or
                origin_transaction.vdatetime is None or
                origin_transaction.value is None
        ):
            return None

        foreign_transactions = self.get_transactions_transfer_related_account(
            origin_account,
            origin_transaction,
        )
        if foreign_transactions is None:
            return None

        for index, foreign_transaction in enumerate(foreign_transactions):
            if (
                    foreign_transaction.counterparty is not None and
                    foreign_transaction.counterparty.account_identification is not None and
                    foreign_transaction.vdatetime is not None and
                    foreign_transaction.value is not None and

                    origin_account.iban == foreign_transaction.counterparty.account_identification and
                    origin_transaction.vdatetime == foreign_transaction.vdatetime and
                    -origin_transaction.value == foreign_transaction.value
            ):
                return foreign_transaction

        return None

    def find_iban_date(
            self,
            origin_account: PowensAccount,
            origin_transaction: PowensTransaction,
    ) -> PowensTransaction | None:

        if (
                origin_account.iban is None or
                origin_transaction.vdate is None or
                origin_transaction.value is None
        ):
            return None

        foreign_transactions = self.get_transactions_transfer_related_account(
            origin_account,
            origin_transaction,
        )
        if foreign_transactions is None:
            return None

        for index, foreign_transaction in enumerate(foreign_transactions):
            if (
                    foreign_transaction.counterparty is not None and
                    foreign_transaction.counterparty.account_identification is not None and
                    foreign_transaction.vdate is not None and
                    foreign_transaction.value is not None and

                    origin_account.iban == foreign_transaction.counterparty.account_identification and
                    origin_transaction.vdate == foreign_transaction.vdate and
                    -origin_transaction.value == foreign_transaction.value
            ):
                return foreign_transaction

        return None

    def find_datetime(
            self,
            origin_account: PowensAccount,
            origin_transaction: PowensTransaction,
    ) -> PowensTransaction | None:

        if (
                origin_transaction.vdatetime is None or
                origin_transaction.value is None
        ):
            return None

        foreign_transactions = self.get_transactions_transfer_related_account(
            origin_account,
            origin_transaction,
        )
        if foreign_transactions is None:
            return None

        for index, foreign_transaction in enumerate(foreign_transactions):
            if (
                    foreign_transaction.vdatetime is not None and
                    foreign_transaction.value is not None and

                    foreign_transaction.type == PowensTransactionType.transfer and
                    origin_transaction.vdatetime == foreign_transaction.vdatetime and
                    -origin_transaction.value == foreign_transaction.value
            ):
                return foreign_transaction

        return None

    def find_date(
            self,
            origin_account: PowensAccount,
            origin_transaction: PowensTransaction,
    ) -> PowensTransaction | None:

        if (
                origin_transaction.vdate is None or
                origin_transaction.value is None
        ):
            return None

        foreign_transactions = self.get_transactions_transfer_related_account(
            origin_account,
            origin_transaction,
        )
        if foreign_transactions is None:
            return None

        for index, foreign_transaction in enumerate(foreign_transactions):
            if (
                    foreign_transaction.vdate is not None and
                    foreign_transaction.value is not None and

                    foreign_transaction.type == PowensTransactionType.transfer and
                    origin_transaction.vdate == foreign_transaction.vdate and
                    -origin_transaction.value == foreign_transaction.value
            ):
                return foreign_transaction

        return None

    def process(
            self,
    ) -> list[Powens2FireflyAccount]:

        for powens_account in self.powens2firefly_accounts:

            for powens_transaction in powens_account.powens_transactions:

                # Transfers
                transfer_transaction = None
                if (
                        transfer_transaction := self.find_iban_datetime(
                            powens_account.powens_account,
                            powens_transaction,
                        )
                ) is not None:
                    ...

                elif (
                        transfer_transaction := self.find_iban_date(
                            powens_account.powens_account,
                            powens_transaction,
                        )
                ) is not None:
                    ...

                elif (
                        transfer_transaction := self.find_datetime(
                            powens_account.powens_account,
                            powens_transaction,
                        )
                ) is not None:
                    ...

                elif (
                        transfer_transaction := self.find_date(
                            powens_account.powens_account,
                            powens_transaction,
                        )
                ) is not None:
                    ...

                elif powens_transaction.type == PowensTransactionType.transfer:
                    ...

                # All other transactions
                elif powens_transaction.value <= 0.0:
                    ...
                elif powens_transaction.value > 0.0:
                    ...
                else:
                    raise ValueError(f"Transaction has no identified value: {powens_transaction}")

