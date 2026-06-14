"""
User interface
"""

from pathlib import Path
import argparse
from datetime import datetime, timedelta, timezone
import logging
import asyncio

from dateutil import parser as dateutil_parser
from powens import PowensClient
from firefly_iii_client.configuration import Configuration
import dateutil

from powens_firefly.handling import handle_credentials, handle_banks, list_all_accounts, handle_mapping
from powens_firefly.process import process_all_transactions
from powens_firefly.upload import upload_transactions

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-v", "-V", "--verbose",
        action="store_true",
        help="Verbose mode, more information is written in the console.",
    )

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
        "--dry",
        action="store_true",
        help="Dry run mode, "
             "Script runs normaly but skips the upload phase to Firefly-III.",
    )

    # parser.add_argument(
    #     "--email-on-failure",
    #     type=str,
    #     help="If script fails in automatic mode, "
    #          "send an email to the specified email address (Not available).",
    # )

    parser.add_argument(
        "--min-date",
        type=dateutil.parser.parse,
        help="Minimum date for transactions.",
    )

    parser.add_argument(
        "--max-date",
        type=dateutil.parser.parse,
        help="Maximum date for transactions.",
    )

    parser.add_argument(
        "--transaction-limit",
        type=int,
        default=1000,
        help="Limit for all transactions fetched (default = 1000)",
    )

    parser.add_argument(
        "--no-transfers",
        action="store_true",
        help="Disable the combining of transactions into transfers considered to be the same between bank accounts.",
    )

    return parser


class Args:
    verbose: bool
    credentials_path: Path
    auto: bool
    dry: bool
    # email_on_failure: str
    min_date: datetime
    max_date: datetime
    transaction_limit: int
    no_transfers: bool


def main(input_args: list | None = None) -> None:

    args = arg_parser().parse_args(input_args, namespace=Args)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled.")

    credentials = handle_credentials(args.credentials_path, auto=args.auto)

    # Powens package is async and tracks async event loops
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    powens_client = PowensClient(
        base_url=credentials.powens.domain,
        access_token=credentials.powens.token,
    )

    token_expiry = (credentials.powens.get_date_acquired() +
                    timedelta(seconds=credentials.powens.expires_in)
    ) if credentials.powens.expires_in is not None else None

    if (
        token_expiry is not None and
        token_expiry <= datetime.now(tz=timezone.utc)
    ):
        print(f"Powens Token renewal is required since it has expired since "
              f"{token_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
        client_secret = input("To Renew, Please enter your application CLIENT SECRET: ").strip()
        auth_token = loop.run_until_complete(powens_client.auth.renew_token(
            client_id=credentials.powens.client_id,
            client_secret=client_secret,
            id_user=credentials.powens.user_id,
            revoke_previous=True,
        ))
        credentials.powens.token = auth_token.access_token
        credentials.save(args.credentials_path)

    firefly_configuration = Configuration(
        host=credentials.firefly.url,
        access_token=credentials.firefly.token,
    )

    if not args.auto:
        print("\n--- Configuration ---")
        handle_banks(
            loop=loop,
            powens_client=powens_client,
            credentials=credentials
        )
        list_all_accounts(
            loop=loop,
            powens_client=powens_client,
            firefly_configuration=firefly_configuration,
            credentials=credentials,
        )
        handle_mapping(
            loop=loop,
            powens_client=powens_client,
            firefly_configuration=firefly_configuration,
            credentials=credentials,
        )
        credentials.save(args.credentials_path)

    firefly_transactions = process_all_transactions(
        credentials=credentials,
        loop=loop,
        powens_client=powens_client,
        firefly_configuration=firefly_configuration,
        limit=args.transaction_limit,
        min_date=args.min_date,
        max_date=args.max_date,
        no_transfers=args.no_transfers,
    )

    if args.verbose:
        for firefly_transaction in firefly_transactions:
            print(firefly_transaction)

    if not args.dry:
        upload_transactions(
            firefly_configuration=firefly_configuration,
            transactions=firefly_transactions,
        )

    loop.run_until_complete(powens_client.aclose())
    loop.close()

if __name__ == "__main__":
    main()
