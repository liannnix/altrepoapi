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

from datetime import datetime
from typing import NamedTuple, Optional, Union

from .base import ErrataServerConnection, JSONObject, JSONResponse
from .base import ErrataServerError  # noqa: F401
from .rusty import Ok, Err, Result, resultify
from .serde import deserialize


CHECK_ROUTE = "check"
UPDATE_ROUTE = "update"
DISCARD_ROUTE = "discard"
REGISTER_ROUTE = "register"


RE_ERRATA_PREFIX = re.compile(r"^ALT-[A-Z]{2,}$")


class ErrataIDServiceResult(NamedTuple):
    id: str
    created: datetime
    updated: datetime


def _into_result(response: JSONResponse) -> Result[ErrataIDServiceResult, Exception]:
    def _deserialize(data: JSONObject):
        return deserialize(ErrataIDServiceResult, data)

    @resultify
    def _extract(response) -> JSONObject:
        return response["errata"]  # type: ignore

    return (
        _extract(response)
        .and_then(_deserialize)
        .map_err(
            lambda e: ErrataServerError(
                f"Failed to parse ErrataServer response due to: {e}"
            )
        )
    )


def _validate_prefix(prefix: str):
    if not RE_ERRATA_PREFIX.match(prefix):
        return Err(ErrataServerError(f"Invalid prefix: {prefix}"))
    return Ok(prefix)


def _validate_year(year: Union[int, None]):
    if year is None:
        return Ok(datetime.now().year)

    if 2000 <= year <= 2999:
        return Ok(year)

    return Err(ErrataServerError(f"Invalid year value: {year}"))


class ErrataIDService:
    """ErrataID service interface class."""

    def __init__(self, url: str) -> None:
        self.service = ErrataServerConnection(url)

    def check(self, id: str) -> ErrataIDServiceResult:
        return (
            self.service.get(CHECK_ROUTE, params={"name": id})
            .and_then(_into_result)
            .unwrap()
        )

    def register(self, prefix: str, year: Optional[int]) -> ErrataIDServiceResult:
        year = _validate_prefix(prefix).op_and(_validate_year(year)).unwrap()
        return (
            self.service.get(REGISTER_ROUTE, params={"prefix": prefix, "year": year})
            .and_then(_into_result)
            .unwrap()
        )

    def update(self, id: str) -> ErrataIDServiceResult:
        return (
            self.service.post(UPDATE_ROUTE, params={"name": id})
            .and_then(_into_result)
            .unwrap()
        )

    def discard(self, id: str) -> ErrataIDServiceResult:
        return (
            self.service.post(DISCARD_ROUTE, params={"name": id})
            .and_then(_into_result)
            .unwrap()
        )
