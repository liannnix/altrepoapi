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

from typing import Any, Iterable
from uuid import UUID

from altrepo_api.api.base import APIWorker
from altrepo_api.utils import make_tmp_table_name

from .sql import sql
from .base import ErrataHandlerError, ErrataPoint
from ..tools.base import Errata, Reference, UserInfo
from ..tools.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_UPDATE,
    CHANGE_SOURCE_KEY,
    CHANGE_SOURCE_AUTO,
    CVE_ID_TYPE,
    DT_NEVER,
    DRY_RUN_KEY,
    TASK_STATE_DONE,
    TASK_PACKAGE_ERRATA_TYPE,
    TASK_PACKAGE_ERRATA_SOURCE,
    VULN_REFERENCE_TYPE,
)
from ..tools.errata import errata_hash
from ..manage import ManageErrata

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

    def _get_bdus_by_cves(self, cve_ids: Iterable[str]) -> dict[str, set[str]]:
        self.status = False
        bdus_by_cve: dict[str, set[str]] = {}

        tmp_table = make_tmp_table_name("cve_ids")

        response = self.send_sql_request(
            self.sql.get_bdus_by_cves.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("cve_id", "String")],
                    "data": [{"cve_id": c} for c in cve_ids],
                },
            ],
        )
        if not self.sql_status:
            return {}
        for el in response:
            bdu_id = el[0]
            for reference in (Reference(t, l) for t, l in zip(el[1], el[2])):
                if reference.type != CVE_ID_TYPE:
                    continue
                bdus_by_cve.setdefault(reference.link, set()).add(bdu_id)

        self.status = True
        return bdus_by_cve

    def _build_erratas_update(
        self,
        erratas_for_update: list[tuple[Errata, str]],
        bdus_by_cve: dict[str, set[str]],
    ) -> list[Errata]:
        # updates erratas with new CVE and related BDU IDs
        erratas: dict[str, Errata] = {}

        for errata, cve_id in erratas_for_update:
            # update existing errata if several CVE ids are added to the same one
            _errata_id = errata.id.id  # type: ignore
            _errata = erratas.get(_errata_id, errata)
            _references = _errata.references
            _linked_vulns = {r.link for r in _references}

            # append new CVE reference if not exists
            if cve_id not in _linked_vulns:
                _references.append(Reference(VULN_REFERENCE_TYPE, cve_id))
            # append new BDU references if not exists
            for bdu_id in bdus_by_cve.get(cve_id, set()):
                if bdu_id not in _linked_vulns:
                    _references.append(Reference(VULN_REFERENCE_TYPE, bdu_id))

            _errata = _errata.update(references=sorted(_references))
            erratas[_errata_id] = _errata.update(hash=errata_hash(_errata))

        return list(erratas.values())

    def _build_erratas_create(
        self, erratas_for_create: list[ErrataPoint], bdus_by_cve: dict[str, set[str]]
    ) -> list[Errata]:
        erratas = []

        for ep in erratas_for_create:
            cve_id = ep.cvm.id
            _references = [Reference(VULN_REFERENCE_TYPE, cve_id)]
            for bdu_id in bdus_by_cve.get(cve_id, set()):
                _references.append(Reference(VULN_REFERENCE_TYPE, bdu_id))

            _references = sorted(_references)

            errata = Errata(
                id=None,
                type=TASK_PACKAGE_ERRATA_TYPE,
                source=TASK_PACKAGE_ERRATA_SOURCE,
                created=DT_NEVER,
                updated=DT_NEVER,
                pkg_hash=ep.task.hash,
                pkg_name=ep.task.name,
                pkg_version=ep.task.version,
                pkg_release=ep.task.release,
                pkgset_name=ep.task.branch,
                task_id=ep.task.task_id,
                subtask_id=ep.task.subtask_id,
                task_state=TASK_STATE_DONE,
                references=_references,
                hash=0,
                is_discarded=False,
            )
            erratas.append(errata.update(hash=errata_hash(errata)))

        return erratas

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

        bdus_by_cve = self._get_bdus_by_cves(cve_ids)
        if not self.status:
            raise ErrataHandlerError("Failed to get BDUs by CVEs")

        for errata in self._build_erratas_update(erratas_for_update, bdus_by_cve):
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

        for errata in self._build_erratas_create(erratas_for_create, bdus_by_cve):
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
        return True
