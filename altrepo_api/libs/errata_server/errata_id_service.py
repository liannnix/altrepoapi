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

from .base import ErrataServer, ErrataServerError, JSONObject


CHECK_ROUTE = "check"
UPDATE_ROUTE = "update"
DISCARD_ROUTE = "discard"
REGISTER_ROUTE = "register"


re_errata_prefix = re.compile(r"^ALT-[A-Z]{2,}$")


class ErrataIDServiceResult(NamedTuple):
    id: str
    created: datetime
    updated: datetime


def _result(response: JSONObject) -> ErrataIDServiceResult:
    data: JSONObject = response["errata"]  # type: ignore
    return ErrataIDServiceResult(
        id=data["id"],  # type: ignore
        created=datetime.fromisoformat(data["created"]),  # type: ignore
        updated=datetime.fromisoformat(data["updated"]),  # type: ignore
    )


def _validate_prefix(prefix: str):
    if not re_errata_prefix.match(prefix):
        raise ErrataServerError("Invalid prefix: %s" % prefix)
    return prefix


def _validate_year(year: Union[int, None]) -> int:
    if year is None:
        return datetime.now().year

    if 2000 <= year <= 2999:
        return year

    raise ErrataServerError("Invalid year value: %s" % year)


class ErrataIDService:
    """ErrataID service interface class."""

    def __init__(self, url: str) -> None:
        self.server = ErrataServer(url)

    def check(self, id: str) -> ErrataIDServiceResult:
        return _result(self.server.get(CHECK_ROUTE, params={"name": id}))  # type: ignore

    def register(self, prefix: str, year: Optional[int]) -> ErrataIDServiceResult:
        prefix = _validate_prefix(prefix)
        return _result(
            self.server.get(
                REGISTER_ROUTE,
                params={"prefix": prefix, "year": _validate_year(year)},
            )  # type: ignore
        )

    def update(self, id: str) -> ErrataIDServiceResult:
        return _result(self.server.post(UPDATE_ROUTE, params={"name": id}))  # type: ignore

    def discard(self, id: str) -> ErrataIDServiceResult:
        return _result(self.server.post(DISCARD_ROUTE, params={"name": id}))  # type: ignore
