# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
from requests import Session
from requests.adapters import HTTPAdapter, Retry
from typing import Any, NamedTuple, Optional, Union

from altrepo_api import read_config

RETRY_ATTEMPTS_TOTAL = 5
RETRY_ALLOWED_METHODS = frozenset(["GET", "HEAD", "POST", "PUT"])
RETRY_STATUS_FORCELIST = [502, 503, 504]
RETRY_BACKOFF_FACTOR_SECONDS = 0.5


class ErrataIDError(Exception):
    pass


class ErrataIDConfig(NamedTuple):
    address: str
    port: int
    prefix: str
    schema: str = "http"

    @property
    def url(self) -> str:
        return f"{self.schema}://{self.address}:{self.port}/"


class ErrataIDResult(NamedTuple):
    id: str
    created: datetime
    updated: datetime


def _result(response: dict[str, Any]) -> ErrataIDResult:
    data = response["errata"]
    return ErrataIDResult(
        id=data["id"],
        created=datetime.fromisoformat(data["created"]),
        updated=datetime.fromisoformat(data["updated"]),
    )


def _validate_year(year: Union[int, None]) -> int:
    if year is None:
        return datetime.now().year

    if 2000 <= year <= 2999:
        return year

    raise ErrataIDError(f"Invalid year value: {year}")


def config_from_url(prefix: str) -> ErrataIDConfig:
    if not read_config.settings.ERRATA_ID_URL:
        raise ErrataIDError("Errata ID server URL should be specified")
    else:
        url = read_config.settings.ERRATA_ID_URL
    url = url.rstrip("/")

    if url.startswith("http://"):
        schema = "http"
    elif url.startswith("https://"):
        schema = "https"
    else:
        raise ErrataIDError(f"Invalid ErrataID URL: {url}")

    try:
        url = url.lstrip(f"{schema}://")
        a, p = url.split(":")
        return ErrataIDConfig(address=a, port=int(p), prefix=prefix, schema=schema)
    except Exception:
        raise ErrataIDError(f"Failed to parse ErrataID URL: {url}")


class ErrataID:
    def __init__(self, config: ErrataIDConfig) -> None:
        self.url = config.url
        self.prefix = config.prefix
        self.session = Session()
        # config retries
        retires = Retry(
            total=RETRY_ATTEMPTS_TOTAL,
            backoff_factor=RETRY_BACKOFF_FACTOR_SECONDS,
            status_forcelist=RETRY_STATUS_FORCELIST,
            allowed_methods=RETRY_ALLOWED_METHODS,
        )
        self.session.mount(f"{config.schema}://", HTTPAdapter(max_retries=retires))
        self._check_service_connection()

    def _check_service_connection(self):
        # XXX: requires ErrataID service version v1.0.6+
        url = self.url + "version"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return None
        except Exception as e:
            raise ErrataIDError(
                f"Failed to connect to ErrataID service at {url}"
            ) from e

    def register(self, year: Optional[int]) -> ErrataIDResult:
        url = self.url + "register"
        try:
            response = self.session.get(
                url, params={"prefix": self.prefix, "year": _validate_year(year)}
            )
            response.raise_for_status()
            return _result(response.json())
        except Exception as e:
            raise ErrataIDError from e

    def check(self, id: str) -> ErrataIDResult:
        url = self.url + "check"
        try:
            response = self.session.get(url, params={"name": id})
            response.raise_for_status()
            return _result(response.json())
        except Exception as e:
            raise ErrataIDError from e

    def update(self, id: str) -> ErrataIDResult:
        url = self.url + "update"
        try:
            response = self.session.post(url, params={"name": id})
            response.raise_for_status()
            return _result(response.json())
        except Exception as e:
            raise ErrataIDError from e
