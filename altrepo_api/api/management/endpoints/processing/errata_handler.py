# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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

from typing import Any
from uuid import UUID

from altrepo_api.api.base import APIWorker

from .sql import sql
from .base import ErrataHandlerError, ErrataPoint
from .helpers import get_bdus_by_cves, build_erratas_create, build_erratas_update
from ..tools.base import Errata, UserInfo
from ..tools.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_UPDATE,
    CHANGE_SOURCE_KEY,
    CHANGE_SOURCE_AUTO,
    DRY_RUN_KEY,
)
from ..errata import ManageErrata

ERRATA_MANAGE_RESPONSE_ERRATA_FIELD = "errata"
ERRATA_MANAGE_RESPONSE_ERRATA_CHANGE_FIELD = "errata_change"


def build_em_payload(
    user_info: UserInfo, action: str, errata: Errata, transaction_id: UUID
) -> dict[str, Any]:
    return {
        "user": user_info.name,
        "reason": f"Errata changed due to: {user_info.reason} [{transaction_id}]",
        "action": action,
        "errata": errata.asdict(),
    }


def build_validation_error_report(worker: APIWorker, args: Any) -> dict[str, Any]:
    return {
        "message": "Request parameters validation error",
        "args": args,
        "details": worker.validation_results,
    }


class ErrataHandler(APIWorker):
    """Handles Errata records modification."""

    def __init__(
        self, connection, user_info: UserInfo, transaction_id: UUID, dry_run: bool
    ):
        self.transaction_id = transaction_id
        self.user_info = user_info
        self.dry_run = dry_run
        self.conn = connection
        self.sql = sql
        self.errata_records: list[dict[str, Any]] = []
        self.errata_change_records: list[dict[str, Any]] = []
        self.is_transaction_completed = False
        super().__init__()

    def _create_errata(self, errata: Errata) -> tuple[bool, dict[str, Any]]:
        args = {
            "payload": build_em_payload(
                self.user_info, CHANGE_ACTION_CREATE, errata, self.transaction_id
            ),
            "transaction_id": self.transaction_id,
            DRY_RUN_KEY: self.dry_run,
            CHANGE_SOURCE_KEY: CHANGE_SOURCE_AUTO,
        }
        me = ManageErrata(connection=self.conn, **args)
        # validate input
        if not me.check_params_post():
            return False, build_validation_error_report(me, args)
        # process errata changes
        response, http_code = me.post()
        return http_code == 200, response

    def _update_errata(self, errata: Errata) -> tuple[bool, dict[str, Any]]:
        args = {
            "payload": build_em_payload(
                self.user_info, CHANGE_ACTION_UPDATE, errata, self.transaction_id
            ),
            "transaction_id": self.transaction_id,
            DRY_RUN_KEY: self.dry_run,
            CHANGE_SOURCE_KEY: CHANGE_SOURCE_AUTO,
        }
        me = ManageErrata(connection=self.conn, **args)
        # validate input
        if not me.check_params_put():
            return False, build_validation_error_report(me, args)
        # process errata changes
        response, http_code = me.put()
        return http_code == 200, response

    def commit(
        self,
        erratas_for_create: list[ErrataPoint],
        erratas_for_update: list[tuple[Errata, str]],
    ) -> None:
        # collect CVE to BDUs mapping
        cve_ids = {cve_id for _, cve_id in erratas_for_update}
        cve_ids.update({p.cvm.id for p in erratas_for_create})

        bdus_by_cve = get_bdus_by_cves(self, cve_ids)
        if not self.status:
            raise ErrataHandlerError("Failed to get BDUs by CVEs")

        for errata in build_erratas_update(self, erratas_for_update, bdus_by_cve):
            status, result = self._update_errata(errata)
            if not status:
                self.store_error(
                    {
                        "message": f"Failed to update Errata in DB: {errata.id}",
                        "details": result,
                    },
                    severity=self.LL.ERROR,
                    http_code=400,
                )
                raise ErrataHandlerError("Failed to update Errata")
            self.errata_records.extend(
                result.get(ERRATA_MANAGE_RESPONSE_ERRATA_FIELD, [])
            )
            self.errata_change_records.extend(
                result.get(ERRATA_MANAGE_RESPONSE_ERRATA_CHANGE_FIELD, [])
            )

        for errata in build_erratas_create(self, erratas_for_create, bdus_by_cve):
            status, result = self._create_errata(errata)
            if not status:
                self.store_error(
                    {
                        "message": (
                            "Failed to create Errata in DB for : "
                            f"{errata.task_id}.{errata.subtask_id} : {errata.pkg_name}"
                        ),
                        "details": result,
                    },
                    severity=self.LL.ERROR,
                    http_code=400,
                )
                raise ErrataHandlerError("Failed to update Errata")
            self.errata_records.extend(
                result.get(ERRATA_MANAGE_RESPONSE_ERRATA_FIELD, [])
            )
            self.errata_change_records.extend(
                result.get(ERRATA_MANAGE_RESPONSE_ERRATA_CHANGE_FIELD, [])
            )

        # all errata updates are completed without errors
        self.is_transaction_completed = True

    def rollback(self) -> bool:
        # FIXME: implement errata changes rollback using `tarnsacion_id`` and
        # `ErrataChangeHistory` table contents here!
        if self.dry_run:
            self.logger.warning("DRY_RUN: Errata manage transaction rollback")
            return True
        self.logger.warning("Errata manage transaction rollback")
        return False
