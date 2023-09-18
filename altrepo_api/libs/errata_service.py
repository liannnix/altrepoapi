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

import re

from datetime import datetime
from requests import Session
from requests.adapters import HTTPAdapter, Retry
from typing import Any, NamedTuple, Optional, Union


RETRY_ATTEMPTS_TOTAL = 5
RETRY_ALLOWED_METHODS = frozenset(["GET", "HEAD", "POST", "PUT"])
RETRY_STATUS_FORCELIST = [502, 503, 504]
RETRY_BACKOFF_FACTOR_SECONDS = 0.5


re_errata_prefix = re.compile(r"^ALT-[A-Z]{2,}$")


class ErrataIDServiceError(Exception):
    pass


class ErrataIDServiceResult(NamedTuple):
    id: str
    created: datetime
    updated: datetime


def _result(response: dict[str, Any]) -> ErrataIDServiceResult:
    data = response["errata"]
    return ErrataIDServiceResult(
        id=data["id"],
        created=datetime.fromisoformat(data["created"]),
        updated=datetime.fromisoformat(data["updated"]),
    )


def _validate_prefix(prefix: str):
    if not re_errata_prefix.match(prefix):
        raise ErrataIDServiceError("Invalid prefix: %s" % prefix)
    return prefix


def _validate_year(year: Union[int, None]) -> int:
    if year is None:
        return datetime.now().year

    if 2000 <= year <= 2999:
        return year

    raise ErrataIDServiceError("Invalid year value: %s" % year)


def _parse_url(url: str) -> tuple[str, str]:
    if not url:
        raise ErrataIDServiceError("Valid service URL should be specified")

    url = url.rstrip("/")

    if url.startswith("http://"):
        schema = "http"
    elif url.startswith("https://"):
        schema = "https"
    else:
        raise ErrataIDServiceError("Invalid service URL: %s" % url)

    try:
        url = url.lstrip(f"{schema}://")
        address, port = url.split(":")
        if not port.isdigit():
            raise ErrataIDServiceError("Failed to parse port from URL: %s" % url)
    except ValueError:
        raise ErrataIDServiceError("Failed to parse service URL: %s" % url)

    return f"{schema}://{address}:{port}/", schema


class ErrataIDService:
    """ErrataID service interface class."""

    def __init__(self, url: str) -> None:
        self.url, self.schema = _parse_url(url)
        self.session = Session()
        # config session retries
        self.session.mount(
            self.schema,
            HTTPAdapter(
                max_retries=Retry(
                    total=RETRY_ATTEMPTS_TOTAL,
                    backoff_factor=RETRY_BACKOFF_FACTOR_SECONDS,
                    status_forcelist=RETRY_STATUS_FORCELIST,
                    allowed_methods=RETRY_ALLOWED_METHODS,
                )
            ),
        )
        self._check_service_connection()

    def _check_service_connection(self):
        url = self.url + "version"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return None
        except Exception as e:
            raise ErrataIDServiceError(
                "Failed to connect to ErrataID service at %s" % url
            ) from e

    def register(self, prefix: str, year: Optional[int]) -> ErrataIDServiceResult:
        prefix = _validate_prefix(prefix)
        url = self.url + "register"
        try:
            response = self.session.get(
                url, params={"prefix": prefix, "year": _validate_year(year)}
            )
            response.raise_for_status()
            return _result(response.json())
        except Exception as e:
            raise ErrataIDServiceError("Failed on %s: %s" % (url, e)) from e

    def check(self, id: str) -> ErrataIDServiceResult:
        url = self.url + "check"
        try:
            response = self.session.get(url, params={"name": id})
            response.raise_for_status()
            return _result(response.json())
        except Exception as e:
            raise ErrataIDServiceError("Failed on %s: %s" % (url, e)) from e

    def update(self, id: str) -> ErrataIDServiceResult:
        url = self.url + "update"
        try:
            response = self.session.post(url, params={"name": id})
            response.raise_for_status()
            return _result(response.json())
        except Exception as e:
            raise ErrataIDServiceError("Failed on %s: %s" % (url, e)) from e
