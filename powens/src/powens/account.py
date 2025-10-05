"""
Powens Account class
"""

from datetime import datetime as dt

from powens.currency import PowensCurrency


class PowensAccount:
    balance: float
    bic: str | None
    bookmarked: int
    coming: None
    coming_balance: float
    company_name: str | None
    currency: PowensCurrency

    deleted: bool | None

    disabled: bool | None
    display: bool
    error: bool | None

    formatted_balance: str
    iban: str | None

    id: int
    id_connection: int
    id_parent: int | None
    id_source: int
    id_type: int
    id_user: int

    information: dict
    last_update: dt | None
    loan: bool | None

    name: str
    number: str | None
    opening_date: dt | None
    original_name: str

    ownership: str

    type: str
    usage: str
    webid: str

    # calculated account ?
    calculated: list | None
    diff: float | None
    diff_percent: float | None
    prev_diff: float | None
    prev_diff_percent: float | None
    valuation: float | None


    def __init__(self, json: dict) -> None:
        self.balance = json["balance"]
        self.bic = json["bic"]
        self.bookmarked = json["bookmarked"]
        self.coming = json["coming"]
        self.coming_balance = json["coming_balance"]
        self.company_name = json["company_name"]

        self.currency = PowensCurrency(json["currency"])

        self.deleted = json["deleted"]

        self.disabled = json["disabled"]
        self.display = json["display"]
        self.error = json["error"]

        self.formatted_balance = json["formatted_balance"]
        self.iban = json["iban"]

        self.id = json["id"]
        self.id_connection = json["id_connection"]
        self.id_parent = json["id_parent"]
        self.id_source = json["id_source"]
        self.id_type = json["id_type"]
        self.id_user = json["id_user"]

        self.information = json["information"]
        self.last_update = json["last_update"]
        self.loan = json["loan"]

        self.name = json["name"]
        self.number = json["number"]
        self.opening_date = json["opening_date"]
        self.original_name = json["original_name"]

        self.ownership = json["ownership"]

        self.type = json["type"]
        self.usage = json["usage"]
        self.webid = json["webid"]

        # calculated account ?
        self.calculated = json.get("calculated")
        if self.calculated is not None:
            for calculated_value in self.calculated:
                setattr(self, calculated_value, json.get(calculated_value))

    def __str__(self) -> str:
        return (
            f"🏦 {self.name} (id={self.id})"
            f" - {self.formatted_balance}"
            f" - {self.currency.id}/{self.currency.symbol}"
        )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} "
            f"wording='{self.name} "
            f"value={self.type} "
            f"balance={self.balance} "
            f"currency_id={self.currency.id}'>"
        )