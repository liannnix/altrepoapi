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

from typing import Any, NamedTuple, TypedDict, TypeVar, Union
from uuid import UUID

from altrepodb_libs import PackageCveMatch

from altrepo_api.api.base import APIWorker

from .sql import sql
from .base import ErrataHandlerError, ErrataPoint, ChangelogErrataPoint, PackageTask
from .helpers import get_bdus_by_cves, build_erratas_create, build_erratas_update
from ..tools.base import Errata, ChangeReason
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
SOURCE_ERRATA_POINT = "cpe"
SOURCE_CHANGELOG = "changelog"
SOURCE_ORDER = {SOURCE_ERRATA_POINT: 0, SOURCE_CHANGELOG: 1}


def build_em_payload(
    user: str, reason: str, action: str, errata: Errata
) -> dict[str, Any]:
    return {"user": user, "reason": reason, "action": action, "errata": errata.asdict()}


def build_validation_error_report(worker: APIWorker, args: Any) -> dict[str, Any]:
    return {
        "message": "Request parameters validation error",
        "args": args,
        "details": worker.validation_results,
    }


def build_errata_details(action: str, source: str, **kwargs) -> dict[str, Any]:
    class BuildDetailsKwargs(TypedDict):
        errata: Errata
        ep: Union[ErrataPoint, ChangelogErrataPoint]
        pcm: PackageCveMatch

    args = BuildDetailsKwargs(kwargs)  # type: ignore

    result: dict[str, Any] = {"action": action, "source": source}

    if (action, source) in (
        (CHANGE_ACTION_CREATE, SOURCE_ERRATA_POINT),
        (CHANGE_ACTION_UPDATE, SOURCE_ERRATA_POINT),
    ):
        result["reason"] = "by CPE version match"

    if (action, source) in (
        (CHANGE_ACTION_CREATE, SOURCE_CHANGELOG),
        (CHANGE_ACTION_UPDATE, SOURCE_CHANGELOG),
    ):
        result["reason"] = "by package changelog"

    if "errata" in args:
        result["errata"] = str(args["errata"].id)

    if "ep" in args:
        ep = args["ep"]
        result["task"] = {
            "branch": ep.task.branch,
            "task_id": ep.task.task_id,
            "subtask_id": ep.task.subtask_id,
            "pkg_name": ep.task.name,
            "pkg_version": ep.task.version,
            "pkg_release": ep.task.release,
        }

        pcm = args["pcm"] if "pcm" in args else None

        result["match"] = {}

        if isinstance(ep, ChangelogErrataPoint):
            result["match"]["cves"] = ep.cve_ids  # type: ignore
        else:
            result["match"]["cve"] = ep.cvm.id
            result["match"]["cpe"] = pcm.pkg_cpe if pcm else ep.cvm.versions.cpe
            result["match"]["versions"] = {  # type: ignore
                "version_start": ep.cvm.versions.version_start,
                "version_start_excluded": ep.cvm.versions.version_start_excluded,
                "version_end": ep.cvm.versions.version_end,
                "version_end_excluded": ep.cvm.versions.version_end_excluded,
            }

    return result


class ErrataCreate(NamedTuple):
    reason: ChangeReason
    ep: Union[ErrataPoint, ChangelogErrataPoint]
    cve_ids: tuple[str, ...]


class ErrataUpdate(NamedTuple):
    reason: ChangeReason
    errata: Errata
    ep: Union[ErrataPoint, ChangelogErrataPoint]
    cve_ids: tuple[str, ...]


ErrataT = Union[ErrataCreate, ErrataUpdate]


T = TypeVar("T", bound=ErrataT)


def sort_erratas_by_source(erratas: list[T]) -> list[T]:
    def key(e: T) -> int:
        return SOURCE_ORDER[e.reason.details["from"]["source"]]

    return sorted(erratas, key=key)


class ErrataHandler(APIWorker):
    """Handles Errata records modification."""

    def __init__(
        self, connection, reason: ChangeReason, transaction_id: UUID, dry_run: bool
    ):
        self.transaction_id = transaction_id
        self.reason = reason
        self.dry_run = dry_run
        self.conn = connection
        self.sql = sql
        self.errata_records: list[dict[str, Any]] = []
        self.errata_change_records: list[dict[str, Any]] = []
        self.is_transaction_completed = False
        self._erratas_to_create: list[ErrataCreate] = []
        self._erratas_to_update: list[ErrataUpdate] = []
        super().__init__()

    def _create_errata(
        self, reason: str, errata: Errata
    ) -> tuple[bool, dict[str, Any]]:
        args = {
            "payload": build_em_payload(
                user=self.reason.actor.name,
                reason=reason,
                action=CHANGE_ACTION_CREATE,
                errata=errata,
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

    def _update_errata(
        self, reason: str, errata: Errata
    ) -> tuple[bool, dict[str, Any]]:
        args = {
            "payload": build_em_payload(
                user=self.reason.actor.name,
                reason=reason,
                action=CHANGE_ACTION_UPDATE,
                errata=errata,
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

    def add_errata_create_from_ep(self, ep: ErrataPoint, pcm: PackageCveMatch):
        reason = self.reason.clone()
        reason.details["from"] = build_errata_details(
            CHANGE_ACTION_CREATE, SOURCE_ERRATA_POINT, ep=ep, pcm=pcm
        )
        self._erratas_to_create.append(
            ErrataCreate(reason=reason, ep=ep, cve_ids=(pcm.vuln_id,))
        )

    def add_errata_create_from_chlog(self, ep: ChangelogErrataPoint):
        reason = self.reason.clone()
        reason.details["from"] = build_errata_details(
            CHANGE_ACTION_CREATE, SOURCE_CHANGELOG, ep=ep
        )
        self._erratas_to_create.append(
            ErrataCreate(reason=reason, ep=ep, cve_ids=ep.cve_ids)
        )

    def add_errata_update_from_ep(
        self, errata: Errata, ep: ErrataPoint, pcm: PackageCveMatch
    ):
        reason = self.reason.clone()
        reason.details["from"] = build_errata_details(
            CHANGE_ACTION_UPDATE, SOURCE_ERRATA_POINT, errata=errata, ep=ep, pcm=pcm
        )
        self._erratas_to_update.append(
            ErrataUpdate(reason=reason, errata=errata, ep=ep, cve_ids=(pcm.vuln_id,))
        )

    def add_errata_update_from_chlog(self, errata: Errata, ep: ChangelogErrataPoint):
        reason = self.reason.clone()
        reason.details["from"] = build_errata_details(
            CHANGE_ACTION_UPDATE, SOURCE_CHANGELOG, errata=errata, ep=ep
        )
        self._erratas_to_update.append(
            ErrataUpdate(reason=reason, errata=errata, ep=ep, cve_ids=ep.cve_ids)
        )

    def commit(self) -> None:
        # collect CVE to BDU mapping
        cve_ids = {c for e in self._erratas_to_update for c in e.cve_ids}
        cve_ids.update({c for e in self._erratas_to_create for c in e.cve_ids})

        bdus_by_cve = get_bdus_by_cves(self, cve_ids)
        if not self.status:
            raise ErrataHandlerError("Failed to get BDUs by CVEs")

        # XXX: combine erratas to be created if any
        pass

        e2c = sort_erratas_by_source(self._erratas_to_create)

        uniq: dict[tuple[str, int, int], set[str]] = {}
        uniq_idxs: dict[tuple[str, int, int], int] = {}

        for idx, e in enumerate(e2c):
            t = e.ep.task
            e_tpl = (t.branch, t.task_id, t.subtask_id)
            if e_tpl not in uniq:
                uniq[e_tpl] = set(e.cve_ids)
                uniq_idxs[e_tpl] = idx
            else:
                diff = set(e.cve_ids).difference(uniq[e_tpl])
                if diff:
                    # TODO: do something with same EP has different CVE IDs
                    print("DBG", diff, e)
                    uniq[e_tpl].update(diff)

        print("DBG", uniq)
        print("DBG", uniq_idxs)

        for key_tpl, idx in uniq_idxs.items():
            cve_ids = uniq[key_tpl]
            ep = e2c[idx]
            # FIXME: create errata here
            pass

        raise RuntimeError("STOP")

        # XXX: combine erratas to be updated if any
        pass

        # for errata in build_erratas_update(erratas_for_update, bdus_by_cve):
        #     status, result = self._update_errata(errata)
        #     if not status:
        #         self.store_error(
        #             {
        #                 "message": f"Failed to update Errata in DB: {errata.id}",
        #                 "details": result,
        #             },
        #             severity=self.LL.ERROR,
        #             http_code=400,
        #         )
        #         raise ErrataHandlerError("Failed to update Errata")
        #     self.errata_records.extend(
        #         result.get(ERRATA_MANAGE_RESPONSE_ERRATA_FIELD, [])
        #     )
        #     self.errata_change_records.extend(
        #         result.get(ERRATA_MANAGE_RESPONSE_ERRATA_CHANGE_FIELD, [])
        #     )

        # for errata in build_erratas_create(erratas_for_create, bdus_by_cve):
        #     status, result = self._create_errata(errata)
        #     if not status:
        #         self.store_error(
        #             {
        #                 "message": (
        #                     "Failed to create Errata in DB for : "
        #                     f"{errata.task_id}.{errata.subtask_id} : {errata.pkg_name}"
        #                 ),
        #                 "details": result,
        #             },
        #             severity=self.LL.ERROR,
        #             http_code=400,
        #         )
        #         raise ErrataHandlerError("Failed to update Errata")
        #     self.errata_records.extend(
        #         result.get(ERRATA_MANAGE_RESPONSE_ERRATA_FIELD, [])
        #     )
        #     self.errata_change_records.extend(
        #         result.get(ERRATA_MANAGE_RESPONSE_ERRATA_CHANGE_FIELD, [])
        #     )

        raise RuntimeError("STOP")

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
