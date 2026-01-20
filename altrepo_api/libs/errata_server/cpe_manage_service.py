# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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
from .pnc_manage_service import PncManageResponse
from .rusty import Result
from .serde import serialize, deserialize

CPE_LIST_ROUTE = "cpe"
CPE_CREATE_ROUTE = "cpe/create"
CPE_DISCARD_ROUTE = "cpe/discard"
CPE_UPDATE_ROUTE = "cpe/update"


class PackageModel(NamedTuple):
    name: str
    branch: str


class CpeGetModel(NamedTuple):
    cpe: str
    state: str
    project_name: str
    packages: list[PackageModel]


class CpeManageGetResponse(NamedTuple):
    cpes: list[CpeGetModel]


class CpeManageRequest(NamedTuple):
    reason: str
    cpe: str
    project_name: str
    package_name: Optional[str]


CpeManageRequest.SKIP_SERIALIZING_IF_NONE = True  # type: ignore


def _deserialize_get(
    response: JSONObject,
) -> Result[CpeManageGetResponse, Exception]:
    return deserialize(CpeManageGetResponse, response).map_err(
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


class CpeManageService(ServiceBase):
    """CPE management service interface class."""

    def get(
        self,
        package_name: str,
        branch: Optional[str] = None,
        state: Optional[Literal["active", "inactive", "candidate"]] = None,
    ) -> CpeManageGetResponse:
        params = {"package_name": package_name}

        if branch:
            params["branch"] = branch
        if state:
            params["state"] = state

        response: Result[JSONObject, Exception] = self.server.get(
            CPE_LIST_ROUTE, params=params
        )  # type: ignore
        return response.and_then(_deserialize_get).unwrap()

    def _post(self, route: str, payload: CpeManageRequest) -> PncManageResponse:
        response: Result[JSONObject, Exception] = self.server.post(
            route=route,
            params=self.params,
            json=serialize(payload),
        )  # type: ignore

        return response.and_then(_deserialize).unwrap()

    def create(
        self,
        reason: str,
        cpe: str,
        project_name: str,
        package_name: Optional[str] = None,
    ) -> PncManageResponse:
        return self._post(
            CPE_CREATE_ROUTE, CpeManageRequest(reason, cpe, project_name, package_name)
        )

    def discard(
        self,
        reason: str,
        cpe: str,
        project_name: str,
        package_name: Optional[str] = None,
    ) -> PncManageResponse:
        return self._post(
            CPE_DISCARD_ROUTE, CpeManageRequest(reason, cpe, project_name, package_name)
        )

    def update(self, reason: str, cpe: str, project_name: str) -> PncManageResponse:
        return self._post(
            CPE_UPDATE_ROUTE, CpeManageRequest(reason, cpe, project_name, None)
        )
