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

from enum import Enum
from typing import Any

from altrepo_api.api.base import APIWorker
from altrepo_api.settings import namespace as settings
from altrepo_api.libs.errata_server.errata_sa_service import (
    ErrataServerError,
    ErrataSAService,
    Errata,
    ErrataJson,
    UserInfo,
    serialize,
    deserialize,
)
from altrepo_api.utils import get_logger, get_real_ip

from .tools.constants import DRY_RUN_KEY


logger = get_logger(__name__)


class ErrataRecordState(Enum):
    ALL = "all"
    ACTIVE = "active"
    INACTIVE = "inactive"


class ErrataJsonType(Enum):
    ALL = "all"
    CVE = "cve"
    CPE = "cpe"
    PACKAGE = "package"


def get_errata_service(
    *, dry_run: bool, access_token: str, user: str, ip: str
) -> ErrataSAService:
    try:
        return ErrataSAService(
            url=settings.ERRATA_MANAGE_URL,
            access_token=access_token,
            user=user,
            ip=ip,
            dry_run=dry_run,
        )
    except ErrataServerError as e:
        logger.error(f"Failed to connect to ErrataSA service: {e}")
        raise RuntimeError("error: %s" % e)


class ManageSa(APIWorker):
    def __init__(self, connection, payload, **kwargs):
        self.payload: dict[str, Any] = payload
        self.dry_run = kwargs.get(DRY_RUN_KEY, False)
        self.conn = connection
        self.args = kwargs
        self.user: UserInfo
        super().__init__()

    def check_params(self) -> bool:
        self.logger.debug(f"args : {self.args}")
        type = self.args.get("type", None)
        filter = self.args.get("filter", None)

        if type:
            type = ErrataJsonType[type.upper()]
            if type != ErrataJsonType.ALL and not filter:
                self.validation_results.append(
                    f"Entry value should be specified for filter of type '{type.name}'"
                )
                return False
            if type == ErrataJsonType.ALL and filter:
                self.validation_results.append(
                    "Entry value should be specified only for filter type is not 'ALL'"
                )
                return False

        return True

    def check_params_post(self) -> bool:
        self.logger.debug(f"args : {self.args}")
        # use direct indeces to fail early
        self.dry_run = self.args[DRY_RUN_KEY]
        self.user = self.user = UserInfo(
            name=self.args["user"],
            ip=get_real_ip(),
        )
        return True

    def get(self):
        state = self.args.get("state", None)
        type = self.args.get("type", None)
        filter_value = self.args.get("filter", None)

        state_filter = (
            ErrataRecordState[state.upper()] if state else ErrataRecordState.ALL
        )
        type_filter = ErrataJsonType[type.upper()] if type else ErrataJsonType.ALL

        service = get_errata_service(dry_run=True, access_token="", user="", ip="")
        try:
            erratas = service.list()
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to get records from Errata Server: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code if e.status_code else 500,
            )

        def filter(errata: Errata) -> bool:
            # filter errata by state
            if state_filter != ErrataRecordState.ALL and (
                (state_filter == ErrataRecordState.ACTIVE and errata.is_discarded)
                or (
                    state_filter == ErrataRecordState.INACTIVE
                    and not errata.is_discarded
                )
            ):
                return False
            # filter errata by type
            if type_filter != ErrataJsonType.ALL and (
                (
                    errata.eh.json is None
                    or (
                        type_filter == ErrataJsonType.CVE
                        and errata.eh.json.vuln_id != filter_value
                    )
                    or (
                        type_filter == ErrataJsonType.CPE
                        and errata.eh.json.vuln_cpe != filter_value
                    )
                    or (
                        type_filter == ErrataJsonType.PACKAGE
                        and errata.eh.json.pkg_name != filter_value
                    )
                )
            ):
                return False

            return True

        res = [e.asdict() for e in erratas if filter(e)]

        if not res:
            return self.store_error(
                {"message": f"No data found in DB for {self.args}"}, http_code=404
            )

        return {"request_args": self.args, "length": len(res), "errata": res}, 200

    def post(self):
        d = deserialize(ErrataJson, self.payload["errata_json"])
        if d.is_err():
            return self.store_error(
                {"message": "Failed to decode request payload"},
                severity=self.LL.ERROR,
                http_code=400,
            )

        service = get_errata_service(
            dry_run=self.dry_run,
            access_token=settings.ERRATA_SERVER_TOKEN,
            user=self.user.name,
            ip=self.user.ip,
        )
        try:
            response = service.create(d.unwrap().sorted())
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to create record in Errata Server: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code if e.status_code else 500,
            )

        return {"request_args": self.args, "result": serialize(response)}, 200  # type: ignore

    def put(self):
        reason = self.payload["reason"]
        prev = deserialize(ErrataJson, self.payload["prev_errata_json"])
        new = deserialize(ErrataJson, self.payload["errata_json"])
        if prev.is_err() or new.is_err():
            return self.store_error(
                {
                    "message": "Failed to decode request payload",
                    "errors": [x.error for x in (prev, new) if x.is_err()],  # type: ignore
                },
                severity=self.LL.ERROR,
                http_code=400,
            )

        service = get_errata_service(
            dry_run=self.dry_run,
            access_token=settings.ERRATA_SERVER_TOKEN,
            user=self.user.name,
            ip=self.user.ip,
        )
        try:
            response = service.update(
                reason=reason,
                prev_errata_json=prev.unwrap().sorted(),
                errata_json=new.unwrap().sorted(),
            )
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to update record in Errata Server: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code if e.status_code else 500,
            )

        return {"request_args": self.args, "result": serialize(response)}, 200  # type: ignore

    def delete(self):
        reason = self.payload["reason"]
        d = deserialize(ErrataJson, self.payload["errata_json"])
        if d.is_err():
            return self.store_error(
                {
                    "message": "Failed to decode request payload",
                    "errors": [d.error],  # type: ignore
                },
                severity=self.LL.ERROR,
                http_code=400,
            )

        service = get_errata_service(
            dry_run=self.dry_run,
            access_token=settings.ERRATA_SERVER_TOKEN,
            user=self.user.name,
            ip=self.user.ip,
        )
        try:
            response = service.discard(
                reason=reason,
                errata_json=d.unwrap().sorted(),
            )
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to discrad record in Errata Server: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code if e.status_code else 500,
            )

        return {"request_args": self.args, "result": serialize(response)}, 200  # type: ignore
