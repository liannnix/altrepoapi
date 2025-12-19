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

import re

from requests import Session, Response
from requests.adapters import HTTPAdapter, Retry
from typing import Any, NamedTuple, Optional, Union
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


def _remove_sensitive_data(msg: str) -> str:
    """Simple helper to clean up sensitive data from error messages."""

    SENSITIVE_PARAMS_MAP = {
        "access_token": "**token**",
        "password": "**password**",
        "refresh_token": "**token**",
    }

    for arg, placeholder in SENSITIVE_PARAMS_MAP.items():
        pattern = rf'{re.escape(arg)}\s*=\s*([^&\s,#]+|"[^"]*"|\'[^\']*\')'

        msg = re.sub(pattern, f"{arg}={placeholder}", msg)

    return msg


def _try_extract_error_message(response: Optional[Response]) -> Optional[str]:
    if response is not None and response.status_code in [400, 401, 404, 409, 500]:
        try:
            json = response.json()
        except Exception:
            return None

        for key in ("error", "comment", "result", "message"):
            if message := json.get(key):
                return message

    return None


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
        response = None
        status_code = 500
        try:
            response = self.session.get(url, params=params)
            status_code = response.status_code
            response.raise_for_status()
            return Ok(response.json())
        except Exception as e:
            err = _try_extract_error_message(response)
            msg = _remove_sensitive_data("Failed on %s: %s" % (url, err or e))
            return Err(ErrataServerError(msg, status_code))

    def post(
        self,
        route: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[JSONObject] = None,
    ) -> Result[JSONResponse, Exception]:
        url = _join_url(self.url, route)
        response = None
        status_code = 500
        try:
            response = self.session.post(url, params=params, json=json)
            status_code = response.status_code
            response.raise_for_status()
            return Ok(response.json())
        except Exception as e:
            err = _try_extract_error_message(response)
            msg = _remove_sensitive_data("Failed on %s: %s" % (url, err or e))
            return Err(ErrataServerError(msg, status_code))

    def put(
        self,
        route: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[JSONObject] = None,
    ) -> Result[JSONResponse, Exception]:
        url = _join_url(self.url, route)
        response = None
        status_code = 500
        try:
            response = self.session.put(url, params=params, json=json)
            status_code = response.status_code
            response.raise_for_status()
            return Ok(response.json())
        except Exception as e:
            err = _try_extract_error_message(response)
            msg = _remove_sensitive_data("Failed on %s: %s" % (url, err or e))
            return Err(ErrataServerError(msg, status_code))


class UserInfo(NamedTuple):
    name: str
    ip: str


class ServiceBase:
    """Errata server endpoint interface service base class."""

    def __init__(
        self, url: str, access_token: Optional[str], user: UserInfo, dry_run: bool
    ) -> None:
        self.server = ErrataServerConnection(url)
        self.user = user
        self.dry_run = dry_run
        self.access_token = access_token

    @property
    def params(self) -> dict[str, Any]:
        params = {
            "user": self.user.name,
            "user_ip": self.user.ip,
            "dry_run": "true" if self.dry_run else "false",
        }

        if self.access_token:
            params["access_token"] = self.access_token
        return params
