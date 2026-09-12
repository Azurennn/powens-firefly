"""User interface."""
import logging
from datetime import UTC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from powens_firefly.cli import Args
    from powens_firefly.console import ConsoleManager

logger = logging.getLogger(__name__)


async def run(args: Args, printer: ConsoleManager) -> None:
    from datetime import datetime, timedelta

    from powens_firefly.handling import handle_credentials
    credentials = await handle_credentials(args.credentials_path, auto=args.auto)

    from powens import PowensClient
    powens_client = PowensClient(
        base_url=credentials.powens.domain,
        access_token=credentials.powens.token,
    )

    token_expiry = (credentials.powens.get_date_acquired() +
                    timedelta(seconds=credentials.powens.expires_in)
    ) if credentials.powens.expires_in is not None else None

    if (
        token_expiry is not None and
        token_expiry <= datetime.now(tz=UTC)
    ):
        print(f"Powens Token renewal is required since it has expired since "
              f"{token_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
        client_secret = input("To Renew, Please enter your application CLIENT SECRET: ").strip()
        auth_token = await powens_client.auth.renew_token(
            client_id=credentials.powens.client_id,
            client_secret=client_secret,
            id_user=credentials.powens.user_id,
            revoke_previous=True,
        )
        credentials.powens.token = auth_token.access_token
        credentials.save(args.credentials_path)

    from firefly import Firefly
    firefly_client = Firefly(
        bearer_token=credentials.firefly.token,
        base_url=credentials.firefly.url,
        timeout=5.0,
    )

    if not args.auto:
        from powens_firefly.console import Color
        print(f"\n{Color.BRIGHT_BLUE}{Color.BOLD} Configuration{Color.RESET}")
        from powens_firefly.handling import handle_banks, handle_mapping, list_all_accounts
        await handle_banks(
            powens_client=powens_client,
            credentials=credentials,
        )
        await list_all_accounts(
            powens_client=powens_client,
            firefly_configuration=firefly_client,
            credentials=credentials,
        )
        await handle_mapping(
            powens_client=powens_client,
            firefly_configuration=firefly_client,
            credentials=credentials,
        )
        credentials.save(args.credentials_path)

    printer.hide_cursor()

    from powens_firefly.process import process_all_transactions
    firefly_transactions = await process_all_transactions(
        credentials=credentials,
        powens_client=powens_client,
        firefly_client=firefly_client,
        limit=args.transaction_limit,
        min_date=args.from_date,
        max_date=args.to_date,
        no_transfers=args.no_transfers,
        printer=printer,
    )

    if logging.getLogger().level <= logging.INFO:
        # TODO get firefly account names
        print("\nProcessed transactions:", flush=True)
        printer.print_all_transactions(firefly_transactions)

    print(
        printer.transactions_summary(
            n_deposits=len([t for t in firefly_transactions if t["type"] == "deposit"]),
            n_withdrawals=len([t for t in firefly_transactions if t["type"] == "withdrawal"]),
            n_transfers=len([t for t in firefly_transactions if t["type"] == "transfer"]),
        ) + " ready",
        flush=True,
    )

    if not args.dry:
        from powens_firefly.upload import upload_transactions
        upload_transactions(
            firefly_client=firefly_client,
            transactions=firefly_transactions,
            printer=printer,
        )

    await powens_client.aclose()
