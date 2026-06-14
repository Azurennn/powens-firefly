"""
Processing functions to detect and convert powens transactions into Firefly-III transactions.
"""
from datetime import datetime, time
from dataclasses import dataclass
from asyncio.events import AbstractEventLoop
from decimal import Decimal
import re
import logging

import firefly_iii_client
from firefly_iii_client.models.transaction_split_store import TransactionSplitStore
from firefly_iii_client.models.transaction_type_property import TransactionTypeProperty
from firefly_iii_client.configuration import Configuration
from powens import PowensClient
from powens import Transaction
from powens.models.account import BankAccount

from powens_firefly.credentials import Credentials

logger = logging.getLogger(__name__)


@dataclass
class FoundTransactionTransfer:
    origin_transaction: Transaction
    counterparty_transaction: Transaction
    origin_account: BankAccount
    counterparty_account: BankAccount
    counterparty_transactions_index: int


@dataclass()
class CommonFireflyTransfer:
    origin_id: int
    counterparty_id: int

    date: datetime
    process_date: datetime
    notes: str

    @classmethod
    def from_found_transaction_transfer(
            cls,
            ftt: FoundTransactionTransfer,
            account_mappings: dict[int, int],
            start_message: str = "Detected from powens-firefly",
    ) -> "CommonFireflyTransfer":
        origin2counterparty = ftt.origin_transaction.value <= 0
        powens_origin_id = ftt.origin_account.id if origin2counterparty \
            else ftt.counterparty_account.id
        firefly_origin_id = account_mappings[powens_origin_id]
        powens_counterparty_id = ftt.counterparty_account.id if origin2counterparty \
            else ftt.origin_account.id
        firefly_counterparty_id = account_mappings[powens_counterparty_id]

        date = get_most_precise_datetime2(
            ftt.origin_transaction.rdatetime,
            ftt.origin_transaction.rdate,
            ftt.counterparty_transaction.rdatetime,
            ftt.counterparty_transaction.rdate,
        )
        process_date = get_most_precise_datetime2(
            ftt.origin_transaction.vdatetime,
            ftt.origin_transaction.vdate,
            ftt.counterparty_transaction.vdatetime,
            ftt.counterparty_transaction.vdate,
        )

        notes = (
            f"{start_message}\n"
            f"{ftt.origin_transaction.wording}\n"
            f"{ftt.origin_transaction.value}{ftt.origin_account.currency.id}\n"
            f"rdate: {ftt.origin_transaction.rdatetime or ftt.origin_transaction.rdate}\n"
            f"vdate: {ftt.origin_transaction.vdatetime or ftt.origin_transaction.vdate}\n"
            f"---\n"
            f"{ftt.counterparty_transaction.wording}\n"
            f"{ftt.counterparty_transaction.value}{ftt.counterparty_account.currency.id}\n"
            f"rdate: {ftt.counterparty_transaction.rdatetime or ftt.counterparty_transaction.rdate}\n"
            f"vdate: {ftt.counterparty_transaction.vdatetime or ftt.counterparty_transaction.vdate}\n"
        )

        return cls(
            origin_id=firefly_origin_id,
            counterparty_id=firefly_counterparty_id,
            date=date,
            process_date=process_date,
            notes=notes,
        )





# TRANSFERS ------------------------------------------------------------------------------------------------------------


def within_tolerance(value: float, reference: float, percent: float = 5.0) -> bool:
    """Check if value is within ±percent% of reference."""
    return abs(value - reference) <= abs(reference) * (percent / 100)


def same_sign(a: Decimal, b: Decimal) -> bool:
    return (a >= 0) == (b >= 0)


def find_transaction_endpoint(
        transaction: Transaction,
        transactions: list[Transaction],
        accounts: dict[int, BankAccount],
) -> FoundTransactionTransfer | None:
    if transaction.counterparty is None:
        return None

    account = accounts[transaction.id_account]
    counterparty_account = None
    for search_account in accounts.values():
        if search_account.iban is not None and transaction.counterparty.account_identification == search_account.iban:
            counterparty_account = search_account
            break
    else:
        return None

    no_commission_value = transaction.value
    if transaction.commission is not None:
        no_commission_value += float(transaction.commission)

    for index, iter_transaction in enumerate(transactions):

        if iter_transaction == transaction:
            continue

        if iter_transaction.id_account != counterparty_account.id:
            continue

        iter_no_commission_value = iter_transaction.value
        if iter_transaction.commission is not None:
            iter_no_commission_value += iter_transaction.commission

        if (
                same_sign(no_commission_value, iter_no_commission_value) or
                account.currency.id != counterparty_account.currency.id or
                abs(no_commission_value) != abs(iter_no_commission_value)
        ):
            continue

        compare_datetime = iter_transaction.rdatetime is not None and transaction.rdatetime is not None
        if compare_datetime and iter_transaction.rdatetime == transaction.rdatetime:
            return FoundTransactionTransfer(
                origin_transaction=transaction,
                counterparty_transaction=iter_transaction,
                origin_account=account,
                counterparty_account=counterparty_account,
                counterparty_transactions_index=index,
            )

        compare_date = iter_transaction.rdate is not None and transaction.rdate is not None
        if not compare_datetime and compare_date and iter_transaction.rdate == transaction.rdate:
            return FoundTransactionTransfer(
                origin_transaction=transaction,
                counterparty_transaction=iter_transaction,
                origin_account=account,
                counterparty_account=counterparty_account,
                counterparty_transactions_index=index,
            )

    return None


def print_powens_transaction(
        transaction: Transaction,
        accounts: dict[int, BankAccount],
) -> None:
    if transaction.rdate is None:
        raise ValueError(f"{transaction} has no rdate")

    print(f"\twording: {transaction.wording}")

    print(f"\tid_account: {transaction.id_account}")
    powens_account = accounts[transaction.id_account]
    print(f"\taccount name: {powens_account.name}")
    print(f"\taccount iban: {powens_account.iban}")

    # print(f"\tapplication_date: {transaction.application_date}")  # same as rdate
    print(f"\tvdate: {transaction.vdate}")
    print(f"\tvdatetime: {transaction.vdatetime}")
    print(f"\trdate: {transaction.rdate}")
    print(f"\trdatetime: {transaction.rdatetime}")

    print(f"\tcounterparty: {transaction.counterparty}")

    print(f"\tvalue: {transaction.value}")
    print(f"\toriginal_value: {transaction.original_value}")  # Not used
    print(f"\toriginal_currency: {transaction.original_currency}")  # Not used
    print(f"\tcommission: {transaction.commission}")  # informative, don't add on to the value, already counted
    print(f"\tcommission_currency: {transaction.commission_currency}")  # Not used


def get_most_precise_datetime2(
        origin_datetime: datetime | None,
        origin_date: date,
        counterparty_datetime: datetime | None,
        counterparty_date: date,
) -> datetime:
    if origin_datetime is not None:
        return origin_datetime
    if counterparty_datetime is not None:
        return counterparty_datetime
    return datetime.combine(origin_date, time(0, 0, 0))


def get_most_precise_datetime(
        src_datetime: datetime | None,
        src_date: date,
) -> datetime:
    if src_datetime is not None:
        return src_datetime
    return datetime.combine(src_date, time(0, 0, 0))


def process_transfers(
        transactions: list[Transaction],
        accounts: dict[int, BankAccount],
        credentials: Credentials,
) -> tuple[list[TransactionSplitStore], list[Transaction]]:
    """
    Find all the Transfers using counterparty iban, value without commission and date
    """
    output_transactions: list[TransactionSplitStore] = []
    processed_transactions_indexes: list[int] = []

    initial_transactions = transactions.copy()

    print("\n--- Detecting Transfers ---")
    for index, transaction in enumerate(initial_transactions):

        if transaction.counterparty is None:
            continue

        if index in processed_transactions_indexes:
            continue

        ftt = find_transaction_endpoint(  # found_transaction_transfer (ftt)
            transaction=transaction,
            transactions=transactions,
            accounts=accounts,
        )

        if ftt is None:
            continue

        processed_transactions_indexes.extend([
            index,
            ftt.counterparty_transactions_index,
        ])
        transactions.remove(transaction)
        transactions.remove(ftt.counterparty_transaction)

        print(f"{'-' * 50}")
        print_powens_transaction(ftt.origin_transaction, accounts=accounts)
        print("===")
        print_powens_transaction(ftt.counterparty_transaction, accounts=accounts)

        common_firefly_transfer = CommonFireflyTransfer.from_found_transaction_transfer(
            ftt=ftt,
            account_mappings=credentials.mapping,
            start_message="Detected Transfer from powens-firefly"
        )

        output_transactions.append(
            TransactionSplitStore(
                type=TransactionTypeProperty.TRANSFER,
                description=ftt.origin_transaction.wording,
                amount=str(abs(ftt.origin_transaction.value)),
                date=common_firefly_transfer.date,
                process_date=common_firefly_transfer.process_date,
                source_id=str(common_firefly_transfer.origin_id),
                destination_id=str(common_firefly_transfer.counterparty_id),
                notes=common_firefly_transfer.notes,
            )
        )

    return output_transactions, transactions


# REVOLUT EXCHANGES ----------------------------------------------------------------------------------------------------


def find_exchange_endpoint(
        transaction: Transaction,
        transactions: list[Transaction],
        account: BankAccount,
        counterparty_account: BankAccount,
) -> FoundTransactionTransfer | None:
    """"""

    for index, iter_transaction in enumerate(transactions):

        if iter_transaction.id_account != counterparty_account.id:
            continue

        compare_datetime = iter_transaction.rdatetime is not None and transaction.rdatetime is not None
        if compare_datetime and iter_transaction.rdatetime == transaction.rdatetime:
            return FoundTransactionTransfer(
                origin_transaction=transaction,
                counterparty_transaction=iter_transaction,
                origin_account=account,
                counterparty_account=counterparty_account,
                counterparty_transactions_index=index,
            )

        compare_date = iter_transaction.rdate is not None and transaction.rdate is not None
        if not compare_datetime and compare_date and iter_transaction.rdate == transaction.rdate:
            return FoundTransactionTransfer(
                origin_transaction=transaction,
                counterparty_transaction=iter_transaction,
                origin_account=account,
                counterparty_account=counterparty_account,
                counterparty_transactions_index=index,
            )

    return None


def extract_currency(text: str):
    match = re.search(r'\b(?:to|in|into|from|for)\s+([A-Z]{3})\b', text)
    return match.group(1) if match else None


def process_revolut_exchanges(
        transactions: list[Transaction],
        accounts: dict[int, BankAccount],
        credentials: Credentials,
        currency_map: dict[str, int],
) -> tuple[list[TransactionSplitStore], list[Transaction]]:
    """
    Find combinations of revolut exchanges.

    Warning
    -------
    Example: If your base account is in EUR and you transfer GBP into USD
    This function is likely to get it wrong, possibly creating the transfer as from your EUR account to your USD account.
    """

    revolut_accounts: dict[str, BankAccount] = {
        account.currency.id: account
        for account in accounts.values()
        if "revolut" in account.name.lower() and account.id_type == 2  # id_type = 2 = checking account
    }
    revolut_accounts_id_list: list[BankAccount] = [rev_account.id for rev_account in revolut_accounts.values()]

    if len(revolut_accounts_id_list) < 2:
        return [], transactions

    output_transactions: list[TransactionSplitStore] = []
    processed_transactions_indexes: list[int] = []

    initial_transactions = transactions.copy()

    print("\n--- Detecting Revolut Exchanges ---")
    for index, transaction in enumerate(initial_transactions):

        if transaction.id_account not in revolut_accounts_id_list:
            continue

        if index in processed_transactions_indexes:
            continue

        if "exchange" not in transaction.wording.lower():
            continue

        current_account = accounts[transaction.id_account]
        currency_type = extract_currency(transaction.wording)
        if currency_type == current_account.currency.id:  # Can only find the 'from' when on its transfer
            continue

        fre = find_exchange_endpoint(  # found_revolut_exchange (fre)
            transaction=transaction,
            transactions=transactions,
            account=current_account,
            counterparty_account=revolut_accounts[currency_type],
        )

        if fre is None:
            continue

        processed_transactions_indexes.extend([
            index,
            fre.counterparty_transactions_index,
        ])

        transactions.remove(fre.origin_transaction)
        transactions.remove(fre.counterparty_transaction)

        print(f"{'-' * 50}")
        print_powens_transaction(fre.origin_transaction, accounts=accounts)
        print("===")
        print_powens_transaction(fre.counterparty_transaction, accounts=accounts)

        common_firefly_transfer = CommonFireflyTransfer.from_found_transaction_transfer(
            ftt=fre,
            account_mappings=credentials.mapping,
            start_message="Detected Revolut Exchange from powens-firefly"
        )

        output_transactions.append(
            TransactionSplitStore(
                type=TransactionTypeProperty.TRANSFER,
                description=fre.origin_transaction.wording,
                amount=str(abs(fre.origin_transaction.value)),
                foreign_amount=str(abs(fre.counterparty_transaction.value)),
                date=common_firefly_transfer.date,
                process_date=common_firefly_transfer.process_date,
                source_id=str(common_firefly_transfer.origin_id),
                currency_id=currency_map[fre.origin_account.currency.id],
                destination_id=str(common_firefly_transfer.counterparty_id),
                foreign_currency_id=currency_map[fre.counterparty_account.currency.id],
                notes=common_firefly_transfer.notes,
            )
        )

    return output_transactions, transactions


# CREDIT-AGRICOLE TRANSFERS --------------------------------------------------------------------------------------------



def find_ca_endpoint(
        transaction: Transaction,
        transactions: list[Transaction],
        account: BankAccount,
        accounts: dict[int, BankAccount],
        allowed_account_ids: list[int],
) -> FoundTransactionTransfer | None:
    """"""

    for index, iter_transaction in enumerate(transactions):

        if iter_transaction.id_account == transaction.id_account:  # Same as initial account, skip
            continue

        if iter_transaction.id_account not in allowed_account_ids:  # Not Credit-agricole account skip
            continue

        if same_sign(iter_transaction.value, transaction.value):  # From one to the other
            continue

        if abs(iter_transaction.value) != abs(transaction.value):  # Assumed no fees for Credit-Agricole transfers
            continue

        compare_datetime = iter_transaction.rdatetime is not None and transaction.rdatetime is not None
        if compare_datetime and iter_transaction.rdatetime == transaction.rdatetime:
            return FoundTransactionTransfer(
                origin_transaction=transaction,
                counterparty_transaction=iter_transaction,
                origin_account=account,
                counterparty_account=accounts[iter_transaction.id_account],
                counterparty_transactions_index=index,
            )

        compare_date = iter_transaction.rdate is not None and transaction.rdate is not None
        if not compare_datetime and compare_date and iter_transaction.rdate == transaction.rdate:
            return FoundTransactionTransfer(
                origin_transaction=transaction,
                counterparty_transaction=iter_transaction,
                origin_account=account,
                counterparty_account=accounts[iter_transaction.id_account],
                counterparty_transactions_index=index,
            )

    return None


def process_credit_agricole(
        transactions: list[Transaction],
        accounts: dict[int, BankAccount],
        credentials: Credentials,
) -> tuple[list[TransactionSplitStore], list[Transaction]]:
    """"""

    # "VIREMENT EMIS WEB"

    # Find COMPTE CHEQUE
    compte_cheque_str = "COMPTE CHEQUE "
    for account in accounts.values():
        if account.name.strip().startswith(compte_cheque_str):
            compte_cheque = account
            break
    else:
        return [], transactions

    compte_cheque_keyword = compte_cheque.name.strip().replace(compte_cheque_str, "")

    ca_accounts: dict[int, BankAccount] = {
        account.id: account
        for account in accounts.values()
        if account.id_connection == compte_cheque.id_connection  # Same connection as COMPTE CHEQUE
    }
    ca_accounts_id_list: list[BankAccount] = [ca_account.id for ca_account in ca_accounts.values()]

    if len(ca_accounts_id_list) < 2:
        return [], transactions

    output_transactions: list[TransactionSplitStore] = []
    processed_transactions_indexes: list[int] = []

    initial_transactions = transactions.copy()

    print("\n--- Detecting Credit-Agricole Transfers ---")
    for index, transaction in enumerate(initial_transactions):

        if transaction.id_account not in ca_accounts_id_list:
            continue

        if index in processed_transactions_indexes:
            continue

        if compte_cheque_keyword not in transaction.wording:
            continue

        current_account = ca_accounts[transaction.id_account]
        fcat = find_ca_endpoint(  # found_ca_transfer (fcat)
            transaction=transaction,
            transactions=transactions,
            account=current_account,
            accounts=accounts,
            allowed_account_ids=ca_accounts_id_list,
        )

        if fcat is None:
            continue

        processed_transactions_indexes.extend([
            index,
            fcat.counterparty_transactions_index,
        ])

        transactions.remove(fcat.origin_transaction)
        transactions.remove(fcat.counterparty_transaction)

        print(f"{'-' * 50}")
        print_powens_transaction(fcat.origin_transaction, accounts=accounts)
        print("===")
        print_powens_transaction(fcat.counterparty_transaction, accounts=accounts)

        common_firefly_transfer = CommonFireflyTransfer.from_found_transaction_transfer(
            ftt=fcat,
            account_mappings=credentials.mapping,
            start_message="Detected Credit-Agricole Transfer from powens-firefly"
        )

        output_transactions.append(
            TransactionSplitStore(
                type=TransactionTypeProperty.TRANSFER,
                description=f"VIREMENT {compte_cheque_keyword}",
                amount=str(abs(fcat.origin_transaction.value)),
                date=common_firefly_transfer.date,
                process_date=common_firefly_transfer.process_date,
                source_id=str(common_firefly_transfer.origin_id),
                destination_id=str(common_firefly_transfer.counterparty_id),
                notes=common_firefly_transfer.notes,
            )
        )

    return output_transactions, transactions


# REMAINING TRANSACTIONS -----------------------------------------------------------------------------------------------


def process_remaning_transactions(
        transactions: list[Transaction],
        accounts: dict[int, BankAccount],
        account_mappings: dict[int, int],
) -> list[TransactionSplitStore]:
    output_transactions: list[TransactionSplitStore] = []

    print("\n--- Processing remaining transactions ---")
    for index, transaction in enumerate(transactions):

        print(f"{'-' * 50}")
        print_powens_transaction(transaction, accounts=accounts)

        precise_rdatetime = get_most_precise_datetime(
            transaction.rdatetime,
            transaction.rdate,
        )
        precise_vdatetime = get_most_precise_datetime(
            transaction.vdatetime,
            transaction.vdate,
        )

        powens_account = accounts[transaction.id_account]
        firefly_id = account_mappings[powens_account.id]

        notes = (
            f"From powens-firefly\n"
            f"{transaction.wording}\n"
            f"{transaction.value}{powens_account.currency.id}\n"
            f"rdate: {transaction.rdatetime or transaction.rdate}\n"
            f"vdate: {transaction.vdatetime or transaction.vdate}\n"
        )

        if transaction.value < 0:
            output_transactions.append(
                TransactionSplitStore(
                    type=TransactionTypeProperty.WITHDRAWAL,
                    description=transaction.wording,
                    amount=str(abs(transaction.value)),
                    date=precise_rdatetime,
                    process_date=precise_vdatetime,
                    source_id=str(firefly_id),
                    notes=notes,
                )
            )
        else:
            output_transactions.append(
                TransactionSplitStore(
                    type=TransactionTypeProperty.DEPOSIT,
                    description=transaction.wording,
                    amount=str(abs(transaction.value)),
                    date=precise_rdatetime,
                    process_date=precise_vdatetime,
                    destination_id=str(firefly_id),
                    notes=notes,
                )
            )

    return output_transactions


# ALL TRANSACTIONS -----------------------------------------------------------------------------------------------------

def process_all_transactions(
        credentials: Credentials,
        loop: AbstractEventLoop,
        powens_client: PowensClient,
        firefly_configuration: Configuration,
        limit: int = 1000,
        min_date: datetime = None,
        max_date: datetime = None,
        no_transfers: bool = False,
) -> list[TransactionSplitStore]:
    """
    Main method to process all types of transactions from powens and convert them into Firefly-III transactions.
    """
    powens_accounts = loop.run_until_complete(powens_client.accounts.list_all(
        user_id=credentials.powens.user_id,
    )).accounts
    powens_accounts_dict = {
        powens_account.id: powens_account
        for powens_account in powens_accounts
        if powens_account.id in credentials.mapping.keys()
    }

    # Getting Firefly Currency ids i.e. 'EUR': 1, 'GBP': x ...
    with firefly_iii_client.ApiClient(firefly_configuration) as api_client:
        currencies_api = firefly_iii_client.CurrenciesApi(api_client)
        currencies = currencies_api.list_currency()
        currency_map = {c.attributes.code: c.id for c in currencies.data}

    print("Fetching Powens transactions")
    powens_transactions = loop.run_until_complete(powens_client.transactions.list_page(
        limit=1000,
        user_id=credentials.powens.user_id,
        include_all=True,
        min_date=min_date,
        max_date=max_date,
    )).transactions

    print("Converting transactions from Powens to Firefly")

    output_transactions: list[TransactionSplitStore] = []

    # Make sure the transaction has been processed by having a vdate and is from an account we want to upload to Firefly
    valid_transactions = [
        t
        for t in powens_transactions
        if (
                t.vdate is not None and
                t.id_account in credentials.mapping.keys()
        )
    ]

    remaining_transactions = sorted(valid_transactions, key=lambda t: t.rdate)

    if not no_transfers:
        found_transfers, remaining_transactions = process_transfers(
            transactions=remaining_transactions,
            accounts=powens_accounts_dict,
            credentials=credentials,
        )
        output_transactions.extend(found_transfers)

        found_revolut_exchanges, remaining_transactions = process_revolut_exchanges(
            transactions=remaining_transactions,
            accounts=powens_accounts_dict,
            credentials=credentials,
            currency_map=currency_map,
        )
        output_transactions.extend(found_revolut_exchanges)

        found_credit_agricole_transfers, remaining_transactions = process_credit_agricole(
            transactions=remaining_transactions,
            accounts=powens_accounts_dict,
            credentials=credentials,
        )
        output_transactions.extend(found_credit_agricole_transfers)

    firefly_remaining_transactions = process_remaning_transactions(
        transactions=remaining_transactions,
        accounts=powens_accounts_dict,
        account_mappings=credentials.mapping,
    )
    output_transactions.extend(firefly_remaining_transactions)

    return output_transactions
