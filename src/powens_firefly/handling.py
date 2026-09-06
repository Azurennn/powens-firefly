"""Handling functions to handle user input."""
import logging
import webbrowser
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import firefly_iii_client
from aioconsole import ainput
from powens import PowensClient

from powens_firefly.console import Color
from powens_firefly.credentials import Credentials, FireflyCredentials, FireflyTokenType, PowensCredentials

if TYPE_CHECKING:
    from pathlib import Path

    from firefly_iii_client.models.autocomplete_account import AutocompleteAccount
    from powens.models.account import BankAccount

logger = logging.getLogger(__name__)


async def handle_credentials(credentials_path: Path, auto: bool) -> Credentials:
    """Handle credentials.

    If credentials file exists, get info from it, all info must be present.
    Else ask user for Powens and Firefly inputs
    and send requests to Powens to obtain token and user_id
    (this creates a new user, a single client can have multiple users)
    """
    if credentials_path.is_file():
        credentials = Credentials.load(credentials_path)
        logger.debug(f"Got credentials from '{credentials_path}'")
    else:
        if auto:
            msg = f"Mode auto activated but no config file was found at '{credentials_path}'"
            raise FileNotFoundError(msg)
        reply = await ainput("Couldn't find credentials file, setup it up ? ([y]/n) ")
        if reply.lower() not in ("yes", "y", ""):
            raise SystemExit(1)

        powens_domain = (await ainput("POWENS DOMAIN: ")).strip()
        powens_client_id = (await ainput("POWENS CLIENT_ID: ")).strip()
        powens_client_secret = (await ainput("POWENS CLIENT_SECRET: ")).strip()

        powens_client = PowensClient(
            base_url=powens_domain,

        )
        auth_token = await powens_client.auth.init_user(
            client_id=powens_client_id,
            client_secret=powens_client_secret,
        )
        token_acquired_date: str = datetime.now(tz=UTC).isoformat()

        firefly_url = (await ainput("FIREFLY URL: ")).strip()

        # reply = (await ainput("FIREFLY TOKEN TYPE (OAuth/[Access Token]): ")).strip()
        #
        # if reply.lower() in ("oauth", "oa"):
        #     firefly_token_type = FireflyTokenType.AccessToken.value
        # elif reply.lower() in ("", "access token", "at", "token"):
        firefly_token_type = FireflyTokenType.BearerToken.value

        firefly_token = (await ainput("FIREFLY TOKEN: ")).strip()

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
        print(f"{Color.BRIGHT_MAGENTA}{Color.BOLD}Credentials file '{credentials_path}' written{Color.RESET}")

    return credentials


async def handle_banks(powens_client: PowensClient, credentials: Credentials) -> None:
    """See and login to banks."""
    while True:
        powens_banks = await powens_client.connections.list_all(
            user_id=credentials.powens.user_id,
        )
        if powens_banks.connections:
            print(f"You currently have {len(powens_banks.connections)} BANKS connected to Powens:")
            for connection in powens_banks.connections:
                print(f"{connection.id} bank-id={connection.id_bank}")
        else:
            print("You currently have NO BANKS connected to Powens")

        reply = (
            await ainput(f"Add a bank connection ? ({'y / [n]' if powens_banks.connections else '[y] / n'}) ")
        ).strip()
        if reply.lower() in ("yes", "y", "1") or (not powens_banks.connections and reply == ""):

            auth_code = await powens_client.auth.generate_code()

            webview_url = powens_client.webview.connect_url(
                client_id=credentials.powens.client_id,
                redirect_uri="https://google.com",
                code=auth_code.code,
            )

            print(f"\n {Color.BRIGHT_CYAN}Visit this URL to connect your bank:{Color.RESET}")
            print(f"{Color.BOLD}{webview_url.url}{Color.RESET}")
            webbrowser.open(webview_url.url)
            await ainput("\n After connecting in your browser, to continue, press [ENTER] ")
        else:
            break


async def list_all_accounts(
        powens_client: PowensClient,
        firefly_configuration: firefly_iii_client.configuration.Configuration,
        credentials: Credentials,
) -> None:
    print(f"\n{Color.BRIGHT_BLUE}{Color.BOLD} Powens Accounts{Color.RESET}")
    powens_accounts = await powens_client.accounts.list_all(
        user_id=credentials.powens.user_id,
    )

    for powens_account in powens_accounts.accounts:
        print(f"{powens_account.id} {powens_account.name} {powens_account.type} "
              f"{powens_account.currency.id} {powens_account.iban}")

    print(f"\n{Color.BRIGHT_BLUE}{Color.BOLD} Firefly-III Accounts{Color.RESET}")
    with firefly_iii_client.ApiClient(firefly_configuration) as api_client:
        api_instance = firefly_iii_client.AutocompleteApi(api_client)
        firefly_accounts = api_instance.get_accounts_ac()

    for firefly_account in firefly_accounts:
        print(f"{firefly_account.id} {firefly_account.name} {firefly_account.type} "
              f"{firefly_account.currency_name}")


def find_account_by_id(
        id: int,
        accounts: list[BankAccount | AutocompleteAccount],
) -> BankAccount | AutocompleteAccount | None:
    for account in accounts:
        if int(account.id) == id:  # Force to be int since AutocompleteAccount.id is a string
            return account
    return None


async def handle_mapping(
        powens_client: PowensClient,
        firefly_configuration: firefly_iii_client.configuration.Configuration,
        credentials: Credentials,
) -> None:

    powens_accounts = await powens_client.accounts.list_all(
        user_id=credentials.powens.user_id,
    )

    with firefly_iii_client.ApiClient(firefly_configuration) as api_client:
        api_instance = firefly_iii_client.AutocompleteApi(api_client)
        firefly_accounts = api_instance.get_accounts_ac()

    for powens_id, firefly_id in credentials.mapping.items():
        powens_account = find_account_by_id(powens_id, powens_accounts.accounts)
        firefly_account = find_account_by_id(firefly_id, firefly_accounts)

        if powens_account is None:
            reply = (await ainput(f"No Powens account found for id={powens_id} "
                          f"(firefly linked id={firefly_id}), remove ? (y/[n]) ")).strip()
            if reply.lower() in ("y", "yes"):
                credentials.mapping.pop(powens_id)
            continue

        if firefly_account is None:
            reply = (await ainput(f"No Firefly account found for id={firefly_id} "
                          f"(powens linked id={powens_id}), remove ? (y/[n]) ")).strip()
            if reply.lower() in ("y", "yes"):
                credentials.mapping.pop(firefly_id)
            continue

    def resolve_name(account_id, accounts, finder) -> str:
        account = finder(account_id, accounts)
        return f"{account_id}. {account.name if account else '??????'}"

    print(f"\n{Color.BRIGHT_BLUE}{Color.BOLD} Mapping Links ({len(credentials.mapping)}){Color.RESET}")

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

    print(f"\n{'Powens'.center(max_p)}    {'Firefly-III'.center(max_f)}")
    for p, f in zip(powens_lines, firefly_lines):
        print(f"{p:<{max_p}} -> {f:<{max_f}}")

    reply = (await ainput("\nContinue with mappings ? (edit in 'credentials.yml' file) (y/[n])")).strip()
    if reply.lower() not in ("y", "yes"):
        raise SystemExit(1)
