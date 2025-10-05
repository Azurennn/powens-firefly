"""
Main user interface
"""

from pathlib import Path
import argparse
from datetime import datetime as dt
from dateutil import parser as dateutil_parser

from pprint import pprint
from datetime import timedelta as td

import firefly_iii_client
from firefly_iii_client.models.autocomplete_account import AutocompleteAccount
from firefly_iii_client.models.transaction_split_store import TransactionSplitStore
from firefly_iii_client.models.transaction_type_property import TransactionTypeProperty

from powens.api import PowensAPI
from powens.transaction import PowensTransactionType
from powens.account import PowensAccount

from powens_firefly.constants import ACCOUNT_TYPES
from powens_firefly.credentials import Credentials
from powens_firefly.credentials import FireflyTokenType
from powens_firefly.convert import Powens2Firefly


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--credentials_path",
        type=Path,
        default=Path("credentials.yml"),
        help="Path to the credentials yaml file.",
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatic mode, "
             "script fails if action required by user, ie redo any authentication.",
    )

    parser.add_argument(
        "--email-on-failure",
        type=str,
        help="If script fails in automatic mode, "
             "send an email to the specified email address.",
    )

    parser.add_argument(
        "--min-date",
        type=str,
        help="Minimum date for transactions.",
    )

    parser.add_argument(
        "--max-date",
        type=str,
        help="Maximum date for transactions.",
    )

    parser.add_argument(
        "--transaction-limit",
        type=int,
        default=1000,
        help="Limit for transactions per bank account, maximum is 1000.",
    )

    parser.add_argument(
        "--no-transfers-combine",
        action="store_true",
        help="Disable the combining of transfers considered to be the same "
             "between bank accounts.",
    )

    return parser


class Args:
    credentials_path: Path
    auto: bool
    email_on_failure: str
    min_date: str | dt
    max_date: str | dt
    transaction_limit: int


def handle_credentials(credentials_path: Path) -> Credentials:
    """
    Handle credentials.

    If credentials file exists, get info from it, all info must be present.
    Else ask user for Powens and Firefly inputs
    and send requests to Powens to obtain token and user_id
    (this creates a new user, a single client can have multiple users)
    """
    if credentials_path.is_file() and credentials_path.exists():
        credentials = Credentials.load(credentials_path)
        print(f"✅ Got crendentials from file {credentials_path}")
    else:
        reply = input(f"Couldn't find credentials file, create a user ? ([y]/n) ")
        if reply.lower() not in ("yes", "y", "1", ""):
            exit()

        powens_domain = input("POWENS DOMAIN: ")
        powens_client_id = input("POWENS CLIENT_ID: ")
        powens_client_secret = input("POWENS CLIENT_SECRET: ")
        powens_token, powens_user_id = PowensAPI(powens_domain).create_user(
            powens_client_id, powens_client_secret)

        firefly_url = input("FIREFLY URL: ")
        while True:
            reply = input("FIREFLY TOKEN TYPE (OAuth/[Access Token]): ")
            if reply.lower() in ("oauth", "oa"):
                firefly_token_type = FireflyTokenType.AccessToken
                break
            elif reply.lower() in ("", "access token", "at"):
                firefly_token_type = FireflyTokenType.BearerToken
                break

            print("Not recognised, try again.")


        firefly_token = input("FIREFLY TOKEN: ")

        credentials = Credentials(
            path=credentials_path,
            powens_domain=powens_domain,
            powens_client_id=powens_client_id,
            powens_user_id=powens_user_id,
            powens_token=powens_token,
            firefly_url=firefly_url,
            firefly_token=firefly_token,
            firefly_token_type=firefly_token_type,
            mapping={},
        )

        credentials.save()
        print("✅ Got token from API and wrote to file for reuse")

    return credentials


def handle_accounts(powens_api: PowensAPI, credentials: Credentials) -> None:
    print("You currently have the following bank accounts linked to Powens:")
    powens_accounts = powens_api.get_accounts(
        credentials.powens.token,
        credentials.powens.user_id,
    )
    for account in powens_accounts:
        print(account)

    reply = input(f"Add more ? (y/[n]) ")
    if reply.lower() in ("yes", "y", "1"):
        connectors = powens_api.get_connectors(credentials.powens.token)
        powens_api.print_connectors(connectors)

        code = powens_api.generate_webview_code(credentials.powens.token)
        webview_url = powens_api.get_webview_url(credentials.powens.client_id, code)

        print(f"\n🔗 Visit this URL to connect your bank:")
        print(f"{webview_url}")
        input("\n📝 After connecting, to continue, press [ENTER] ")


def list_all_accounts(
    powens_api: PowensAPI,
    firefly_configuration: firefly_iii_client.configuration.Configuration,
    credentials: Credentials,
) -> None:
    print("\n--- All Accounts ---")

    powens_accounts = powens_api.get_accounts(
        credentials.powens.token,
        credentials.powens.user_id,
    )

    with firefly_iii_client.ApiClient(firefly_configuration) as api_client:
        api_instance = firefly_iii_client.AutocompleteApi(api_client)
        firefly_accounts = api_instance.get_accounts_ac(types=ACCOUNT_TYPES)

    print(f"{' ' * 20} --- POWENS Accounts ({len(powens_accounts)}) --- {' ' * 20}|"
          f"{' ' * 10} --- FIREFLY III Accounts ({len(firefly_accounts)}) ---")

    for index in range(max(len(powens_accounts), len(firefly_accounts))):
        powens_account_str = (
            f"{powens_accounts[index].name} (id={powens_accounts[index].id}) - "
            f"{powens_accounts[index].currency.id}"
        ) if index < len(powens_accounts) else ""

        firefly_account_str = (
            f"{firefly_accounts[index].name} (id={firefly_accounts[index].id}) - "
            f"{firefly_accounts[index].currency_code}"
        ) if index < len(firefly_accounts) else ""

        print(f"{powens_account_str:<50} | {firefly_account_str:<50}")


def find_account_by_id(
    id: int,
    accounts: list[PowensAccount | AutocompleteAccount]
) -> PowensAccount | AutocompleteAccount | None:
    for account in accounts:
        if int(account.id) == id:  # Force to be int since AutocompleteAccount.id is a string
            return account
    return None

def handle_mapping(
    powens_api: PowensAPI,
    firefly_configuration: firefly_iii_client.configuration.Configuration,
    credentials: Credentials
) -> None:

    powens_accounts = powens_api.get_accounts(
        credentials.powens.token,
        credentials.powens.user_id,
    )

    with firefly_iii_client.ApiClient(firefly_configuration) as api_client:
        api_instance = firefly_iii_client.AutocompleteApi(api_client)
        firefly_accounts = api_instance.get_accounts_ac(types=ACCOUNT_TYPES)

    print("\nOpening Mappings...")
    output = {}
    for powens_id, firefly_id in credentials.mapping.items():
        powens_account = find_account_by_id(powens_id, powens_accounts)
        firefly_account = find_account_by_id(firefly_id, firefly_accounts)

        if powens_account is None:
            reply = input(f"No Powens account found for id={powens_id} "
                          f"(firefly linked id={firefly_id}), remove ? (y/[n])")
            if reply.lower() in ("y", "yes"):
                credentials.mapping.pop(powens_id)
            continue

        if firefly_account is None:
            reply = input(f"No Firefly account found for id={firefly_id} "
                          f"(powens  linked id={powens_id}), remove ? (y/[n])")
            if reply.lower() in ("y", "yes"):
                credentials.mapping.pop(firefly_id)
            continue

        output.update({
            f"{powens_account.name} (id={powens_account.id})" : f"{firefly_account.name} (id={firefly_account.id})"
        })

    print(f"\n--- Mapping Links ({len(output)}) ---")
    for powens, firefly in output.items():
        print(f"{powens:<50} -> {firefly:<50}")


def main(input_args: list | None = None) -> None:

    args = arg_parser().parse_args(input_args, namespace=Args)

    if args.min_date is not None:
        args.min_date = dateutil_parser.parse(args.min_date)

    if args.max_date is not None:
        args.max_date = dateutil_parser.parse(args.max_date)

    credentials = handle_credentials(args.credentials_path.absolute())

    powens_api = PowensAPI(credentials.powens.domain)

    firefly_configuration = firefly_iii_client.configuration.Configuration(
        host=credentials.firefly.url,
        access_token=credentials.firefly.token,
    )

    if not args.auto:
        print(f"\n--- Setup ---")
        handle_accounts(powens_api, credentials)
        list_all_accounts(powens_api, firefly_configuration, credentials)
        handle_mapping(powens_api, firefly_configuration, credentials)
        credentials.save()

    print(f"\n--- Connections ---")
    connections = powens_api.get_connections(
        credentials.powens.token, credentials.powens.user_id)
    powens_api.print_connections(connections)

    print(f"\n--- User id {credentials.powens.user_id} ---")

    accounts = powens_api.get_accounts(
        credentials.powens.token,
        credentials.powens.user_id
    )

    powens_account_transactions = {}

    for account in accounts:
        print(account)
        print(account.iban)

        transactions = powens_api.get_transactions(
            credentials.powens.token,
            credentials.powens.user_id,
            account.id,
            min_date=args.min_date,
            max_date=args.max_date,
            limit=args.transaction_limit,
        )

        powens_account_transactions.update({
            account: transactions
        })

        print(f"\ttransactions: {len(transactions)}")
        for transaction in transactions:
            print(f"\t\t{transaction}")

            if transaction.vdate is None:
                raise ValueError(f"{transaction} has no vdate")

            if transaction.type == PowensTransactionType.transfer:
                print(f"\t\t\tcounterparty: {transaction.counterparty}")
                if transaction.counterparty:
                    print(f"\t\t\tcounterparty.iban: {transaction.counterparty.account_identification}")
                print(f"\t\t\toriginal_value: {transaction.original_value}")

            if "Exchanged" in transaction.wording:
                print(f"\t\t\tvalue: {transaction.value}")
                print(f"\t\t\taccount_currency: {account.currency}")
                print(f"\t\t\toriginal_value: {transaction.original_value}")
                print(f"\t\t\toriginal_currency: {transaction.original_currency}")
                print(f"\t\t\tcommission: {transaction.commission}")
                print(f"\t\t\tcommission_currency: {transaction.commission_currency}")



    with firefly_iii_client.ApiClient(firefly_configuration) as api_client:

        # Create an instance of the API class
        api_instance = firefly_iii_client.TransactionsApi(api_client)

        firefly_transaction = TransactionSplitStore(
            type=TransactionTypeProperty.TRANSFER,
            date=dt.now(),
            description="Test dummy",
            amount="1.0",
            source_id="1",
            destination_id="1",
            # tags="",
            process_date=dt.now() + td(days=1),
        )

        transaction_store = firefly_iii_client.TransactionStore(
            apply_rules=True,
            error_if_duplicate_hash=True,
            transactions=[
                firefly_transaction
            ]
        )

        print("Sending firefly transactions...")
        try:
            # Store a new transaction
            api_response = api_instance.store_transaction(transaction_store)
            print("The response of TransactionsApi->store_transaction:\n")
            pprint(api_response)
        except Exception as e:
            print("Exception when calling TransactionsApi->store_transaction: %s\n" % e)

if __name__ == "__main__":
    main()
