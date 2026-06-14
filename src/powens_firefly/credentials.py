"""
Class to store credentials
"""
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from pydantic.dataclasses import dataclass

import yaml

logger = logging.getLogger(__name__)


@dataclass
class PowensCredentials:
    domain: str
    client_id: str
    user_id: int
    token: str
    date_acquired_utc: str
    expires_in: int | None

    def get_date_acquired(self) -> datetime:
        return datetime.fromisoformat(self.date_acquired_utc).astimezone(tz=timezone.utc)

    def set_data_acquired(self, date_time: datetime) -> None:
        self.date_acquired_utc = date_time.isoformat()


class FireflyTokenType(Enum):
    BearerToken = "BearerToken"
    """In Firefly = Access Tokens"""
    AccessToken = "AccessToken"
    """In Firefly = OAuth"""

    def __repr__(self) -> str:
        return f"<FireflyTokenType {self.value}>"


@dataclass
class FireflyCredentials:
    url: str
    token: str
    token_type: str


@dataclass
class Credentials:
    powens: PowensCredentials
    firefly: FireflyCredentials
    mapping: dict[int, int]

    def save(self, file_path: Path) -> None:
        with file_path.open("w") as f:
            yaml.dump(
                data={
                    "powens": self.powens.__dict__,
                    "firefly": self.firefly.__dict__,
                    "mapping": self.mapping,
                },
                stream=f,
            )

    @staticmethod
    def load(file_path: Path) -> "Credentials":

        with file_path.open("r") as f:
            data = yaml.safe_load(f)

        return Credentials(
            powens=PowensCredentials(**data["powens"]),
            firefly=FireflyCredentials(**data["firefly"]),
            mapping=data["mapping"],
        )
