"""
Powens API class
"""

import requests
from datetime import datetime as dt
import webbrowser

from pprint import pprint

from powens.account import PowensAccount
from powens.transaction import PowensTransaction


class PowensAPI:

    domain: str
    api_base: str

    def __init__(
            self,
            domain: str,
    ) -> None:
        self.domain = domain
        self.api_base = f"https://{self.domain}/2.0"

    def create_user(self, client_id: str, client_secret: str) -> tuple[str, int]:
        """Authenticate and return access token and id_user"""
        resp = requests.post(
            f"{self.api_base}/auth/init",
            data={
                "client_id": client_id,
                "client_secret": client_secret
            }
        )
        resp.raise_for_status()
        return resp.json()["auth_token"], resp.json()["id_user"]

    def generate_webview_code(self, user_token: str, token_type: str = "singleAccess") -> str:
        """Generate temporary code for webview"""
        headers = {"Authorization": f"Bearer {user_token}"}

        # The correct endpoint from the documentation
        resp = requests.get(
            f"{self.api_base}/auth/token/code",
            headers=headers,
            params={"type": token_type}
        )
        resp.raise_for_status()
        result = resp.json()
        code = result["code"]
        return code

    def get_webview_url(self, client_id: str, code: str) -> str:
        """Get different webview URLs"""
        return (
            f"https://webview.powens.com/en/manage?"
            f"domain={self.domain}&"
            f"client_id={client_id}&"
            f"code={code}"
        )

    def open_webview(self, user_token: str, client_id: str):
        """Open webview"""
        code = self.generate_webview_code(user_token)
        url = self.get_webview_url(client_id, code)
        webbrowser.open(url)

    def get_connectors(self, token: str):
        """List available bank connectors"""
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{self.api_base}/connectors", headers=headers)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def print_connectors(connectors: dict) -> None:
        """Print available bank account connectors"""
        print("Available connectors:")
        for connector in connectors["connectors"]:
            print(f"  - {connector['name']} (id: {connector['id']})")

    def get_connections(self, token: str, user_id: int):
        """Get bank accounts linked to a user"""
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{self.api_base}/users/{user_id}/connections", headers=headers)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def print_connections(connections: dict) -> None:
        """Print bank account connections"""
        for connection in connections["connections"]:
            print(
                f"  - id: {connection["id"]}, "
                f"id_bank: {connection["id_bank"]}, "
                f"created: {connection["created"]}, "
                f"updated: {connection["last_update"]}, "
                f"next_update: {connection["next_try"]}, "
                f"expire: {connection["expire"]}, "
                f"state: {connection["state"]}"
            )

    def get_accounts(self, token: str, user_id: int) -> list[PowensAccount]:
        """Get bank accounts linked to a user"""
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{self.api_base}/users/{user_id}/accounts",
            headers=headers
        )
        resp.raise_for_status()
        accounts = [PowensAccount(json_account) for json_account in resp.json()["accounts"]]
        return accounts

    def get_transactions(
            self,
            token: str,
            user_id: int,
            account_id: int,
            limit: int = 1000,
            min_date: dt | None = None,
            max_date: dt | None = None,
            deleted: bool | None = None,
    ) -> list[PowensTransaction]:
        """Fetch transactions for an account from the past N days"""
        headers = {"Authorization": f"Bearer {token}"}

        params: dict[str, int | bool | str] = {
            "limit": limit,
        }
        if min_date is not None:
            params.update({"min_date": min_date.isoformat()})
        if max_date is not None:
            params.update({"max_date": max_date.isoformat()})
        if deleted is not None:
            params.update({"deleted": deleted})

        resp = requests.get(
            f"{self.api_base}/users/{user_id}/accounts/{account_id}/transactions",
            headers=headers,
            params=params
        )

        resp.raise_for_status()
        transactions = [PowensTransaction(json_transaction) for json_transaction in resp.json()["transactions"]]
        return transactions
