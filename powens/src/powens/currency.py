"""
Powens Currency class
"""

from typing import Any

from powens.utils import parse_optional_date


class PowensCurrency:
    id: str
    name: str
    symbol: str
    precision: int

    # Extras not documented by Powens
    __datetime: str | None | Any
    __marketcap: str | None | Any
    __prefix: bool | None | Any
    __crypto: bool | None | Any

    def __init__(self, json: dict[str, Any]) -> None:
        self.id = json.get("id")
        self.name = json.get("name")
        self.symbol = json.get("symbol")
        self.precision = json.get("precision")

        self.__datetime = parse_optional_date(json.get("datetime"))
        self.__marketcap = json.get("marketcap")
        self.__prefix = json.get("prefix")
        self.__crypto = json.get("crypto")

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} id={self.id}, name={self.name}, precision={self.precision}>"
        )
