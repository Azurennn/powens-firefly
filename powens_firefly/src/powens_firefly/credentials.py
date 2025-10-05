"""
Class to store credentials
"""

from pathlib import Path
from enum import Enum
import yaml

class PowensCredentials:
    domain: str
    client_id: str
    user_id: int
    token: str

    def __init__(
            self,
            domain: str,
            client_id: str,
            user_id: int,
            token: str,
    ):
        self.domain = domain
        self.client_id = client_id
        self.user_id = user_id
        self.token = token


class FireflyTokenType(Enum):

    BearerToken = "BearerToken" #
    """In Firefly = Access Tokens"""

    AccessToken = "AccessToken"
    """In Firefly = OAuth"""

    def __repr__(self) -> str:
        return self.value


class FireflyCredentials:
    url: str
    token: str
    token_type: FireflyTokenType

    def __init__(
            self,
            url: str,
            token: str,
            token_type: FireflyTokenType
    ):
        self.url = url
        self.token = token
        self.token_type = token_type


class Credentials:
    path: Path
    powens: PowensCredentials
    firefly: FireflyCredentials
    mapping: dict

    def __init__(
            self,
            path: Path,
            powens_domain: str,
            powens_client_id: str,
            powens_user_id: int,
            powens_token: str,
            firefly_url: str,
            firefly_token: str,
            firefly_token_type: FireflyTokenType,
            mapping: dict,
    ) -> None:
        self.path = path
        self.powens = PowensCredentials(
            powens_domain,
            powens_client_id,
            powens_user_id,
            powens_token,
        )
        self.firefly = FireflyCredentials(
            firefly_url,
            firefly_token,
            firefly_token_type,
        )
        self.mapping = mapping

    def save(self) -> None:
        with self.path.open("w") as f:
            yaml.dump({
                "powens": {
                    "domain": self.powens.domain,
                    "client_id": self.powens.client_id,
                    "user_id": self.powens.user_id,
                    "token": self.powens.token,
                },
                "firefly": {
                    "url": self.firefly.url,
                    "token": self.firefly.token,
                    "token_type": self.firefly.token_type.value,
                },
                "mapping": self.mapping,
            }, f)

    @staticmethod
    def load(file_path: Path) -> "Credentials":

        with file_path.open("r") as f:
            data = yaml.safe_load(f)

        return Credentials(
            path=file_path,
            powens_domain=data["powens"]["domain"],
            powens_client_id=data["powens"]["client_id"],
            powens_user_id=data["powens"]["user_id"],
            powens_token=data["powens"]["token"],

            firefly_url=data["firefly"]["url"],
            firefly_token=data["firefly"]["token"],
            firefly_token_type=FireflyTokenType(data["firefly"]["token_type"]),
            mapping=data["mapping"],
        )
