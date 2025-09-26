# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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

from requests import Session
from requests.adapters import HTTPAdapter, Retry
from typing import Any, Optional, Union
from urllib.parse import urlparse, urlunparse

from .rusty import Ok, Err, Result


RETRY_ATTEMPTS_TOTAL = 5
RETRY_ALLOWED_METHODS = frozenset(["GET", "HEAD", "POST", "PUT"])
RETRY_STATUS_FORCELIST = [500, 502, 503, 504]
RETRY_BACKOFF_FACTOR_SECONDS = 0.5

VERSION_ROUTE = "version"

# type aliases
JSONValue = Union[
    str, int, float, bool, None, dict[str, "JSONValue"], list["JSONValue"]
]
JSONObject = dict[str, JSONValue]
JSONResponse = Union[JSONObject, list[JSONObject]]


# exceptions
class ErrataServerError(Exception):
    """Base ErrataServer interface exception class."""

    def __init__(self, message, status_code: Optional[int] = None):
        super().__init__(f"{message} [code: {status_code}]")
        self.status_code = status_code


# helpers
def _parse_url(url: str) -> Result[tuple[str, str, str], Exception]:
    """Parses URL string and returns tuple of schema, base URL and normalized URL."""

    try:
        parsed = urlparse(url)
        return Ok(
            (
                parsed.scheme,
                urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")),
                urlunparse(parsed),
            )
        )
    except (ValueError, TypeError):
        return Err(ErrataServerError("Failed to parse service URL: %s" % url))


def _join_url(base_url: str, route: str) -> str:
    return f"{base_url.removesuffix('/')}/{route.removeprefix('/')}"


# base service connection class
class ErrataServerConnection:
    def __init__(self, url: str) -> None:
        schema, base_url, self.url = _parse_url(url).unwrap()
        self.session = Session()
        # config session retries
        self.session.mount(
            schema,
            HTTPAdapter(
                max_retries=Retry(
                    total=RETRY_ATTEMPTS_TOTAL,
                    backoff_factor=RETRY_BACKOFF_FACTOR_SECONDS,
                    status_forcelist=RETRY_STATUS_FORCELIST,
                    allowed_methods=RETRY_ALLOWED_METHODS,
                )
            ),
        )
        # check service connection
        try:
            response = self.session.get(_join_url(base_url, VERSION_ROUTE))
            response.raise_for_status()
        except Exception as e:
            raise ErrataServerError(
                "Failed to connect to Errata Server service at %s" % url
            ) from e

    def get(
        self, route: str, *, params: Optional[dict[str, Any]] = None
    ) -> Result[JSONResponse, Exception]:
        url = _join_url(self.url, route)
        status_code = 500
        try:
            response = self.session.get(url, params=params)
            status_code = response.status_code
            response.raise_for_status()
            return Ok(response.json())
        except Exception as e:
            return Err(ErrataServerError("Failed on %s: %s" % (url, e), status_code))

    def post(
        self,
        route: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[JSONObject] = None,
    ) -> Result[JSONResponse, Exception]:
        url = _join_url(self.url, route)
        status_code = 500
        try:
            response = self.session.post(url, params=params, json=json)
            status_code = response.status_code
            response.raise_for_status()
            return Ok(response.json())
        except Exception as e:
            return Err(ErrataServerError("Failed on %s: %s" % (url, e), status_code))

    def put(
        self,
        route: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[JSONObject] = None,
    ) -> Result[JSONResponse, Exception]:
        url = _join_url(self.url, route)
        status_code = 500
        try:
            response = self.session.put(url, params=params, json=json)
            status_code = response.status_code
            response.raise_for_status()
            return Ok(response.json())
        except Exception as e:
            return Err(ErrataServerError("Failed on %s: %s" % (url, e), status_code))
