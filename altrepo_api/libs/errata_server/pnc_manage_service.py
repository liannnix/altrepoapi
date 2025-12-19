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

from typing import Literal, NamedTuple, Optional

from .base import ErrataServerError, JSONObject, ServiceBase
from .errata_sa_service import AffectedPCM, ChangeReason
from .rusty import Result
from .serde import serialize, deserialize

PNC_LIST_ROUTE = "pnc"
PNC_CREATE_ROUTE = "pnc/create"
PNC_DISCARD_ROUTE = "pnc/discard"
# PNC_UPDATE_ROUTE = "pnc/update"


class PncRecord(NamedTuple):
    pkg_name: str
    pnc_state: str
    pnc_result: str
    pnc_type: str
    pnc_source: str


class PncChangeRecord(NamedTuple):
    id: str
    type: str
    source: str
    origin: str
    pnc: PncRecord
    reason: ChangeReason


class PncManageGetResponse(NamedTuple):
    pncs: list[PncRecord]


class PncManageRequest(NamedTuple):
    reason: str
    package_name: str
    project_name: str


class PncManageResponse(NamedTuple):
    result: str
    pnc: list[PncRecord]
    pnc_change: list[PncChangeRecord]
    affected_pcm: list[AffectedPCM]


def _deserialize_get(
    response: JSONObject,
) -> Result[PncManageGetResponse, Exception]:
    return deserialize(PncManageGetResponse, response).map_err(
        lambda e: ErrataServerError(
            f"Failed to parse ErrataServer response due to: {e}"
        )
    )


def _deserialize(response: JSONObject) -> Result[PncManageResponse, Exception]:
    return deserialize(PncManageResponse, response).map_err(
        lambda e: ErrataServerError(
            f"Failed to parse ErrataServer response due to: {e}"
        )
    )


class PncManageService(ServiceBase):
    """PNC management service interface class."""

    def get(
        self,
        package_name: Optional[str] = None,
        project_name: Optional[str] = None,
        state: Optional[Literal["active", "inactive", "candidate"]] = None,
    ) -> PncManageGetResponse:
        params = {}

        if package_name:
            params["package_name"] = package_name
        if project_name:
            params["project_name"] = project_name
        if state:
            params["state"] = state

        response: Result[JSONObject, Exception] = self.server.get(
            PNC_LIST_ROUTE, params=params
        )  # type: ignore
        return response.and_then(_deserialize_get).unwrap()

    def _post(self, route: str, payload: PncManageRequest) -> PncManageResponse:
        response: Result[JSONObject, Exception] = self.server.post(
            route=route,
            params=self.params,
            json=serialize(payload),
        )  # type: ignore

        return response.and_then(_deserialize).unwrap()

    def create(
        self, reason: str, package_name: str, project_name: str
    ) -> PncManageResponse:
        return self._post(
            PNC_CREATE_ROUTE, PncManageRequest(reason, package_name, project_name)
        )

    def discard(
        self, reason: str, package_name: str, project_name: str
    ) -> PncManageResponse:
        return self._post(
            PNC_DISCARD_ROUTE, PncManageRequest(reason, package_name, project_name)
        )
