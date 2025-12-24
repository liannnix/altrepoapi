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

from datetime import datetime
from typing import NamedTuple

from .base import ErrataServerError, JSONObject, ServiceBase
from .errata_sa_service import Errata, ErrataHistory, ErrataChange
from .rusty import Result
from .serde import serialize, deserialize

ERRATA_LIST_ROUTE = "errata"
ERRATA_CREATE_ROUTE = "errata/create"
ERRATA_DISCARD_ROUTE = "errata/discard"
ERRATA_UPDATE_ROUTE = "errata/update"


class Vulnerability(NamedTuple):
    id: str
    type_: str
    summary: str
    score: float
    severity: str
    url: str
    modified_date: datetime
    published_date: datetime
    references: list[str]
    is_valid: bool


class ErrataManageGetResponse(NamedTuple):
    errata: Errata
    vulns: list[Vulnerability]


class ErrataManageResponse(NamedTuple):
    result: str
    errata: list[Errata]
    errata_change: list[ErrataChange]


class ErrataManageRequest(NamedTuple):
    reason: str
    errata: ErrataHistory


def _deserialize_get(
    response: JSONObject,
) -> Result[ErrataManageGetResponse, Exception]:
    return deserialize(ErrataManageGetResponse, response).map_err(
        lambda e: ErrataServerError(
            f"Failed to parse ErrataServer response due to: {e}"
        )
    )


def _deserialize(response: JSONObject) -> Result[ErrataManageResponse, Exception]:
    return deserialize(ErrataManageResponse, response).map_err(
        lambda e: ErrataServerError(
            f"Failed to parse ErrataServer response due to: {e}"
        )
    )


class ErrataManageService(ServiceBase):
    """Errata management service interface class."""

    def _post(self, route: str, payload: ErrataManageRequest) -> ErrataManageResponse:
        response: Result[JSONObject, Exception] = self.server.post(
            route,
            params=self.params,
            json=serialize(payload),
        )  # type: ignore

        return response.and_then(_deserialize).unwrap()

    def get(self, errata_id: str) -> ErrataManageGetResponse:
        response: Result[JSONObject, Exception] = self.server.get(
            ERRATA_LIST_ROUTE, params={"errata_id": errata_id}
        )  # type: ignore
        return response.and_then(_deserialize_get).unwrap()

    def create(self, reason: str, errata: ErrataHistory) -> ErrataManageResponse:
        return self._post(ERRATA_CREATE_ROUTE, ErrataManageRequest(reason, errata))

    def discard(self, reason: str, errata: ErrataHistory) -> ErrataManageResponse:
        return self._post(ERRATA_DISCARD_ROUTE, ErrataManageRequest(reason, errata))

    def update(self, reason: str, errata: ErrataHistory) -> ErrataManageResponse:
        return self._post(ERRATA_UPDATE_ROUTE, ErrataManageRequest(reason, errata))
