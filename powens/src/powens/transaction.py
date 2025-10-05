"""
Powens transaction class
"""
from enum import Enum
from typing import Any
from datetime import datetime as dt
import dateutil.parser as dateutil_parser

from powens.utils import parse_optional_date
from powens.currency import PowensCurrency

class PowensTransactionType(Enum):
    transfer = "transfer"
    """Transfer"""
    order = "order"
    """Order"""
    check = "check"
    """Check"""
    deposit = "deposit"
    """Mandatory/voluntary deposits, contributions, money transfers"""
    payback = "payback"
    """Payback"""
    withdrawal = "withdrawal"
    """Withdrawal"""
    loan_repayment = "loan_repayment"
    """Loan payment"""
    bank = "bank"
    """Bank fees"""
    card = "card"
    """Card operation"""
    deferred_card = "deferred_card"
    """Deferred card operation"""
    summary_card = "summary_card"
    """Monthly debit of a deferred card"""
    unknown = "unknown"
    """Unknown transaction type"""
    market_order = "market_order"
    """Market order"""
    market_fee = "market_fee"
    """Fees regarding a market order"""
    arbitrage = "arbitrage"
    """Arbitrage"""
    profit = "profit"
    """Positive earnings from interests/coupons/dividends"""
    refund = "refund"
    """With opposition to a payback, a refund has a negative value"""
    payout = "payout"
    """Transfer from the e-commerce account (eg; Stripe) to the bank account"""
    payment = "payment"
    """Payment made with a payment method different from card"""
    fee = "fee"
    """Fee made with a payment method different from card.
    Differs from bank type because it considers only tax/commission"""

class PowensCounterParty:
    label: str | None
    account_scheme_name: str | None
    account_identification: str | None
    type: str | None

    def __init__(self, json: dict[str, Any]):
        self.label = json.get("label")
        self.account_scheme_name = json.get("account_scheme_name")
        self.account_identification = json.get("account_identification")
        self.type = json.get("type")

    def __repr__(self) -> str:
        return (
            f"<PowensCounterParty "
            f"label={self.label}, "
            f"type={self.type}, "
            f"account_scheme_name={self.account_scheme_name}, "
            f"account_identification={self.account_identification}>"
        )


class PowensTransaction:
    # Basic attributes
    id: int
    id_account: int
    application_date: dt | None
    date: dt
    datetime: dt | None

    # Dates (parsed / reconciled / booked / validated)
    vdate: dt | None
    vdatetime: dt | None
    rdate: dt
    rdatetime: dt | None
    bdate: dt | None
    bdatetime: dt | None

    # Values
    value: float | None
    gross_value: float | None
    type: PowensTransactionType

    # Wording
    original_wording: str
    simplified_wording: str
    wording: str | None
    id_category: int

    # State info
    date_scraped: dt
    coming: bool
    active: bool
    id_cluster: int | None
    comment: str | None
    last_update: dt | None
    deleted: dt | None

    original_value: float | None
    original_gross_value: float | None
    original_currency: PowensCurrency | None

    commission: float | None
    commission_currency: PowensCurrency | None

    card: str | None

    counterparty: PowensCounterParty | None

    # Extras, undefined in API documentation
    webid: str | Any
    stemmed_wording: str | Any
    state: str | Any
    formatted_value: str | Any
    documents_count: int | Any
    informations: dict[str, Any] | Any
    country: str | None | Any
    details: str | None | Any

    def __init__(self, transaction_dict: dict[str, Any]):
        # Basic attributes
        self.id = transaction_dict.get("id")
        self.id_account = transaction_dict.get("id_account")
        self.webid = transaction_dict.get("webid")
        self.application_date = transaction_dict.get("application_date")
        self.date = dateutil_parser.parse(transaction_dict.get("date"))
        self.datetime = parse_optional_date(transaction_dict.get("datetime"))

        # Dates (parsed / reconciled / booked / validated)
        self.rdate = dateutil_parser.parse(transaction_dict.get("rdate"))
        self.rdatetime = parse_optional_date(transaction_dict.get("rdatetime"))
        self.vdate = parse_optional_date(transaction_dict.get("vdate"))
        self.vdatetime = parse_optional_date(transaction_dict.get("vdatetime"))
        self.bdate = parse_optional_date(transaction_dict.get("bdate"))
        self.bdatetime = parse_optional_date(transaction_dict.get("bdatetime"))

        # Values
        self.value = transaction_dict.get("value")
        self.gross_value = transaction_dict.get("gross_value")
        self.original_value = transaction_dict.get("original_value")
        self.original_gross_value = transaction_dict.get("original_gross_value")

        if transaction_dict.get("original_currency") is not None:
            self.original_currency = PowensCurrency(transaction_dict["original_currency"])
        else:
            self.original_currency = None

        self.commission = transaction_dict.get("commission")

        if transaction_dict.get("commission_currency") is not None:
            self.commission_currency = PowensCurrency(transaction_dict["commission_currency"])
        else:
            self.commission_currency = None

        # Wording
        self.original_wording = transaction_dict.get("original_wording")
        self.simplified_wording = transaction_dict.get("simplified_wording")
        self.stemmed_wording = transaction_dict.get("stemmed_wording")
        self.wording = transaction_dict.get("wording")

        # State info
        self.id_category = transaction_dict.get("id_category")
        self.state = transaction_dict.get("state")
        self.date_scraped = transaction_dict.get("date_scraped")
        self.last_update = transaction_dict.get("last_update")
        self.deleted = transaction_dict.get("deleted")
        self.active = transaction_dict.get("active")
        self.coming = transaction_dict.get("coming")

        # Metadata
        self.id_cluster = transaction_dict.get("id_cluster")
        self.comment = transaction_dict.get("comment")
        self.type = PowensTransactionType(transaction_dict.get("type"))
        self.formatted_value = transaction_dict.get("formatted_value")
        self.documents_count = transaction_dict.get("documents_count")
        self.informations = transaction_dict.get("informations", {})
        self.country = transaction_dict.get("country")
        self.card = transaction_dict.get("card")
        self.details = transaction_dict.get("details")

        # Counterparty (nested dict)
        counterparty = transaction_dict.get("counterparty")
        if counterparty is not None:
            self.counterparty = PowensCounterParty(counterparty)
        else:
            self.counterparty = None

    def __str__(self) -> str:
        printed_wording = self.wording if len(self.wording) <= 40 else f"{self.wording[:37]}..."
        printed_date = self.datetime if self.datetime is not None \
            else self.date
        printed_vdate = self.vdatetime if self.vdatetime is not None \
            else self.vdate
        return (
            f"💸 {printed_date} | "
            f"{self.state:^8} | "
            f"{self.type.value:^8} | "
            f"{printed_wording:<40} | "
            f"{self.formatted_value}"
        )

    def __repr__(self):
        return f"<Transaction id={self.id} wording='{self.wording} value={self.value}'>"
