"""
Handling functions to handle user input.
"""
from pathlib import Path
import asyncio
from asyncio.events import AbstractEventLoop
import webbrowser
from datetime import datetime, timezone

from powens import PowensClient
from powens.models.account import BankAccount
import firefly_iii_client
from firefly_iii_client.models.autocomplete_account import AutocompleteAccount

from powens_firefly.credentials import Credentials, PowensCredentials, FireflyCredentials, FireflyTokenType


def handle_credentials(credentials_path: Path, auto: bool) -> Credentials:
    """
    Handle credentials.

    If credentials file exists, get info from it, all info must be present.
    Else ask user for Powens and Firefly inputs
    and send requests to Powens to obtain token and user_id
    (this creates a new user, a single client can have multiple users)
    """
    if credentials_path.is_file():
        credentials = Credentials.load(credentials_path)
        print(f"✅ Got crendentials from file '{credentials_path}'")
    else:
        if auto:
            raise FileNotFoundError(f"Mode auto activated but no config file was found at '{credentials_path}'")
        reply = input("Couldn't find credentials file, setup it up ? ([y]/n) ")
        if reply.lower() not in ("yes", "y", "1", ""):
            raise SystemExit(1)

        powens_domain = input("POWENS DOMAIN: ").strip()
        powens_client_id = input("POWENS CLIENT_ID: ").strip()
        powens_client_secret = input("POWENS CLIENT_SECRET: ").strip()

        powens_client = PowensClient(
            base_url=powens_domain,

        )
        auth_token = asyncio.run(powens_client.auth.init_user(
            client_id=powens_client_id,
            client_secret=powens_client_secret,
        ))
        token_acquired_date: str = datetime.now(tz=timezone.utc).isoformat()

        firefly_url = input("FIREFLY URL: ").strip()

        firefly_token_type = None
        while firefly_token_type is None:
            reply = input("FIREFLY TOKEN TYPE (OAuth/[Access Token]): ").strip()

            if reply.lower() in ("oauth", "oa"):
                firefly_token_type = FireflyTokenType.AccessToken.value
            elif reply.lower() in ("", "access token", "at", "token"):
                firefly_token_type = FireflyTokenType.BearerToken.value

            if firefly_token_type is None:
                print("Not recognised, try again.")

        firefly_token = input("FIREFLY TOKEN: ").strip()

        credentials = Credentials(
            powens=PowensCredentials(
                domain=powens_domain,
                client_id=powens_client_id,
                user_id=auth_token.id_user,
                token=auth_token.auth_token,
                date_acquired_utc=token_acquired_date,
                expires_in=auth_token.expires_in,
            ),
            firefly=FireflyCredentials(
                url=firefly_url,
                token=firefly_token,
                token_type=firefly_token_type,
            ),
            mapping={},
        )

        credentials.save(file_path=credentials_path)
        print("✅ Got token from API and wrote to file for reuse")

    return credentials


def handle_banks(loop: AbstractEventLoop, powens_client: PowensClient, credentials: Credentials) -> None:
    """See and login to banks."""
    while True:
        powens_banks = loop.run_until_complete(powens_client.connections.list_all(
            user_id=credentials.powens.user_id,
        ))
        if powens_banks.connections:
            print(f"You currently have {len(powens_banks.connections)} BANKS connected to Powens:")
            for connection in powens_banks.connections:
                print(f"{connection.id} bank-id={connection.id_bank}")
        else:
            print("You currently have NO BANKS connected to Powens")

        reply = input(f"Add a bank connection ? ({'y / [n]' if powens_banks.connections else '[y] / n'}) ").strip()
        if reply.lower() in ("yes", "y", "1") or (not powens_banks.connections and reply == ""):

            auth_code = loop.run_until_complete(powens_client.auth.generate_code())

            webview_url = powens_client.webview.connect_url(
                client_id=credentials.powens.client_id,
                redirect_uri="https://google.com",
                code=auth_code.code,
            )

            print("\n🔗 Visit this URL to connect your bank:")
            print(f"{webview_url.url}")
            webbrowser.open(webview_url.url)
            input("\n📝 After connecting in your browser, to continue, press [ENTER] ")
        else:
            break


def list_all_accounts(
        loop: AbstractEventLoop,
        powens_client: PowensClient,
        firefly_configuration: firefly_iii_client.configuration.Configuration,
        credentials: Credentials,
) -> None:
    print("\n--- Powens Accounts ---")
    powens_accounts = loop.run_until_complete(powens_client.accounts.list_all(
        user_id=credentials.powens.user_id,
    ))

    for powens_account in powens_accounts.accounts:
        print(f"{powens_account.id} {powens_account.name} {powens_account.type} "
              f"{powens_account.currency.id} {powens_account.iban}")

    print("\n--- Firefly-III Accounts ---")
    with firefly_iii_client.ApiClient(firefly_configuration) as api_client:
        api_instance = firefly_iii_client.AutocompleteApi(api_client)
        firefly_accounts = api_instance.get_accounts_ac()

    for firefly_account in firefly_accounts:
        print(f"{firefly_account.id} {firefly_account.name} {firefly_account.type} "
              f"{firefly_account.currency_name}")


def find_account_by_id(
        id: int,
        accounts: list[BankAccount | AutocompleteAccount]
) -> BankAccount | AutocompleteAccount | None:
    for account in accounts:
        if int(account.id) == id:  # Force to be int since AutocompleteAccount.id is a string
            return account
    return None


def handle_mapping(
        loop: AbstractEventLoop,
        powens_client: PowensClient,
        firefly_configuration: firefly_iii_client.configuration.Configuration,
        credentials: Credentials
) -> None:

    powens_accounts = loop.run_until_complete(powens_client.accounts.list_all(
        user_id=credentials.powens.user_id,
    ))

    with firefly_iii_client.ApiClient(firefly_configuration) as api_client:
        api_instance = firefly_iii_client.AutocompleteApi(api_client)
        firefly_accounts = api_instance.get_accounts_ac()

    for powens_id, firefly_id in credentials.mapping.items():
        powens_account = find_account_by_id(powens_id, powens_accounts.accounts)
        firefly_account = find_account_by_id(firefly_id, firefly_accounts)

        if powens_account is None:
            reply = input(f"No Powens account found for id={powens_id} "
                          f"(firefly linked id={firefly_id}), remove ? (y/[n]) ").strip()
            if reply.lower() in ("y", "yes"):
                credentials.mapping.pop(powens_id)
            continue

        if firefly_account is None:
            reply = input(f"No Firefly account found for id={firefly_id} "
                          f"(powens linked id={powens_id}), remove ? (y/[n]) ").strip()
            if reply.lower() in ("y", "yes"):
                credentials.mapping.pop(firefly_id)
            continue

    def resolve_name(account_id, accounts, finder):
        account = finder(account_id, accounts)
        return f"{account_id}. {account.name if account else '??????'}"

    print(f"\n--- Mapping Links ({len(credentials.mapping)}) ---")

    powens_lines = [
        resolve_name(pid, powens_accounts.accounts, find_account_by_id)
        for pid in credentials.mapping
    ]
    firefly_lines = [
        resolve_name(fid, firefly_accounts, find_account_by_id)
        for fid in credentials.mapping.values()
    ]

    max_p = max(len(line) for line in powens_lines)
    max_f = max(len(line) for line in firefly_lines)
    max_p = max(max_p, len("Powens"))
    max_f = max(max_f, len("Firefly-III"))

    print(f"\n{'Powens'.center(max_p)} || {'Firefly-III'.center(max_f)}")
    for p, f in zip(powens_lines, firefly_lines):
        print(f"{p:<{max_p}} -> {f:<{max_f}}")

    reply = input("\nAre these mappings adequate ? (if not exits) (y/[n])").strip()
    if reply.lower() not in ("y", "yes"):
        raise SystemExit(1)
