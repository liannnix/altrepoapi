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
from .base import ErrataHandlerError, ErrataPoint, ChangelogErrataPoint
from .helpers import get_bdus_by_cves
from ..errata import ManageErrata
from ..tools.base import Errata, ChangeReason, PncRecordType
from ..tools.constants import (
    CHANGE_ACTION_DISCARD,
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_UPDATE,
    CHANGE_SOURCE_KEY,
    CHANGE_SOURCE_AUTO,
    DRY_RUN_KEY,
    DT_NEVER,
    ERRATA_MANAGE_RESPONSE_ERRATA_FIELD,
    ERRATA_MANAGE_RESPONSE_ERRATA_CHANGE_FIELD,
    KEY_ACTION,
    KEY_CPE,
    KEY_PNC,
    KEY_STATE,
    KEY_PACKAGE,
    KEY_PROJECT,
    SOURCE_CHANGELOG,
    SOURCE_CPE_DISCRAD,
    SOURCE_PNC_DISCRAD,
    SOURCE_ERRATA_POINT,
    SOURCE_ORDER,
    TASK_STATE_DONE,
    TASK_PACKAGE_ERRATA_TYPE,
    TASK_PACKAGE_ERRATA_SOURCE,
    VULN_REFERENCE_TYPE,
)
from ..tools.errata import Reference, errata_hash


class ErrataCreate(NamedTuple):
    reason: ChangeReason
    ep: Union[ErrataPoint, ChangelogErrataPoint]
    cve_ids: tuple[str, ...]


class ErrataUpdate(NamedTuple):
    reason: ChangeReason
    errata: Errata
    ep: Union[ErrataPoint, ChangelogErrataPoint]
    cve_ids: tuple[str, ...]


class ErrataDiscard(NamedTuple):
    reason: ChangeReason
    errata: Errata
    cpe: str
    cve_ids: tuple[str, ...]


# type aliases
ErrataT = Union[ErrataCreate, ErrataUpdate, ErrataDiscard]
ErrataTupleT = tuple[str, int, int]


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
        self._erratas_to_discard: list[ErrataDiscard] = []
        super().__init__()

    def _create_errata(
        self, et: ErrataCreate, errata: Errata
    ) -> tuple[bool, dict[str, Any]]:
        args = {
            "payload": build_manage_errata_payload(
                user=self.reason.user.name,
                reason=build_reason_string(et),
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
        # update 'ManageErrata' reason object with details
        update_manage_errata_reason(me, et)
        # process errata changes
        try:
            response, http_code = me.post()
            return http_code == 200, response
        except Exception as e:
            return False, {
                "message": (
                    f"Failed to create errata for {errata.pkg_name} "
                    f"[{errata.task_id}:{errata.subtask_id}]"
                ),
                "reason": f"Exception: {e}",
            }

    def _update_errata(
        self, et: ErrataUpdate, errata: Errata
    ) -> tuple[bool, dict[str, Any]]:
        args = {
            "payload": build_manage_errata_payload(
                user=self.reason.user.name,
                reason=build_reason_string(et),
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
        # update 'ManageErrata' reason object with details
        update_manage_errata_reason(me, et)
        # process errata changes
        try:
            response, http_code = me.put()
            return http_code == 200, response
        except Exception as e:
            return False, {
                "message": f"Failed to update errata {errata.id}",
                "reason": f"Exception: {e}",
            }

    def _discard_errata(
        self, et: ErrataDiscard, errata: Errata
    ) -> tuple[bool, dict[str, Any]]:
        # Errata references is not empty after CVE and BDU discard -> update
        if errata.references:
            return self._update_errata(et, errata)  # type: ignore
        # discard Errata
        args = {
            "payload": build_manage_errata_payload(
                user=self.reason.user.name,
                reason=build_reason_string(et),
                action=CHANGE_ACTION_DISCARD,
                # XXX: use original errata state here to be discarded
                errata=et.errata,
            ),
            "transaction_id": self.transaction_id,
            DRY_RUN_KEY: self.dry_run,
            CHANGE_SOURCE_KEY: CHANGE_SOURCE_AUTO,
        }
        me = ManageErrata(connection=self.conn, **args)
        # validate input
        if not me.check_params_delete():
            return False, build_validation_error_report(me, args)
        # update 'ManageErrata' reason object with details
        update_manage_errata_reason(me, et)
        # process errata changes
        try:
            response, http_code = me.delete()
            return http_code == 200, response
        except Exception as e:
            return False, {
                "message": f"Failed to discard errata {errata.id}",
                "reason": f"Exception: {e}",
            }

    def _process_create_errata(self, bdus_by_cve: dict[str, set[str]]) -> None:
        # sort and merge erratas to be created if any
        erratas_to_create = sort_erratas_by_source(self._erratas_to_create)

        uniq_cves: dict[ErrataTupleT, set[str]] = {}
        uniq_idxs: dict[ErrataTupleT, int] = {}

        for idx, errata in enumerate(erratas_to_create):
            t = errata.ep.task
            e_tpl = (t.branch, t.task_id, t.subtask_id)
            if e_tpl not in uniq_cves:
                uniq_cves[e_tpl] = set(errata.cve_ids)
                uniq_idxs[e_tpl] = idx
            else:
                diff = set(errata.cve_ids).difference(uniq_cves[e_tpl])
                if diff:
                    # merge EPs has different CVE IDs
                    uniq_cves[e_tpl].update(diff)

        # store erratas to be created
        for key_tpl, idx in uniq_idxs.items():
            cve_ids = uniq_cves[key_tpl]
            et = erratas_to_create[idx]
            # create errata here
            errata = build_errata_create(et, cve_ids, bdus_by_cve)
            status, result = self._create_errata(et, errata)
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

    def _process_update_errata(self, bdus_by_cve: dict[str, set[str]]) -> None:
        # sort and merge erratas to be updated if any
        erratas_to_update = sort_erratas_by_source(self._erratas_to_update)

        uniq_cves: dict[ErrataTupleT, set[str]] = {}
        uniq_idxs: dict[ErrataTupleT, int] = {}

        for idx, errata in enumerate(erratas_to_update):
            t = errata.ep.task
            e_tpl = (t.branch, t.task_id, t.subtask_id)
            if e_tpl not in uniq_cves:
                uniq_cves[e_tpl] = set(errata.cve_ids)
                uniq_idxs[e_tpl] = idx
            else:
                diff = set(errata.cve_ids).difference(uniq_cves[e_tpl])
                if diff:
                    # merge EPs has different CVE IDs
                    uniq_cves[e_tpl].update(diff)

        # store erratas to be created
        for key_tpl, idx in uniq_idxs.items():
            cve_ids = uniq_cves[key_tpl]
            et = erratas_to_update[idx]
            # update errata here
            errata = build_errata_update(et, cve_ids, bdus_by_cve)
            status, result = self._update_errata(et, errata)
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

    def _process_discrad_errata(self, bdus_by_cve: dict[str, set[str]]) -> None:
        erratas_to_discard = self._erratas_to_discard[:]

        uniq_cves: dict[ErrataTupleT, set[str]] = {}
        uniq_idxs: dict[ErrataTupleT, int] = {}

        for idx, errata in enumerate(erratas_to_discard):
            e_tpl = (
                errata.errata.pkgset_name,
                errata.errata.task_id,
                errata.errata.subtask_id,
            )
            if e_tpl not in uniq_cves:
                uniq_cves[e_tpl] = set(errata.cve_ids)
                uniq_idxs[e_tpl] = idx
            else:
                diff = set(errata.cve_ids).difference(uniq_cves[e_tpl])
                if diff:
                    # merge EPs has different CVE IDs
                    uniq_cves[e_tpl].update(diff)

        # store erratas to be created
        for key_tpl, idx in uniq_idxs.items():
            cve_ids = uniq_cves[key_tpl]
            et = erratas_to_discard[idx]
            # update errata here
            errata = build_errata_discard(et, cve_ids, bdus_by_cve)
            status, result = self._discard_errata(et, errata)
            if not status:
                self.store_error(
                    {
                        "message": f"Failed to discard or update Errata in DB: {errata.id}",
                        "details": result,
                    },
                    severity=self.LL.ERROR,
                    http_code=400,
                )
                raise ErrataHandlerError("Failed to discrad or update Errata")
            self.errata_records.extend(
                result.get(ERRATA_MANAGE_RESPONSE_ERRATA_FIELD, [])
            )
            self.errata_change_records.extend(
                result.get(ERRATA_MANAGE_RESPONSE_ERRATA_CHANGE_FIELD, [])
            )

        pass

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

    def add_errata_discard(
        self, type: PncRecordType, errata: Errata, cpe: str, cve_ids: tuple[str, ...]
    ):
        reason = self.reason.clone()
        reason.details["from"] = build_errata_details(
            CHANGE_ACTION_DISCARD,
            SOURCE_CPE_DISCRAD if type == PncRecordType.CPE else SOURCE_PNC_DISCRAD,
            errata=errata,
            cpe=cpe,
            cve_ids=cve_ids,
        )
        self._erratas_to_discard.append(
            ErrataDiscard(reason=reason, errata=errata, cpe=cpe, cve_ids=cve_ids)
        )

    def commit(self) -> None:
        # collect CVE to BDU mapping
        cve_ids = {c for e in self._erratas_to_update for c in e.cve_ids}
        cve_ids.update({c for e in self._erratas_to_create for c in e.cve_ids})
        cve_ids.update({c for e in self._erratas_to_discard for c in e.cve_ids})

        bdus_by_cve = get_bdus_by_cves(self, cve_ids)
        if not self.status:
            raise ErrataHandlerError("Failed to get BDUs by CVEs")

        self._process_create_errata(bdus_by_cve)
        self._process_update_errata(bdus_by_cve)
        self._process_discrad_errata(bdus_by_cve)

        # all errata updates are completed without errors
        self.is_transaction_completed = True


# helper functions
T = TypeVar("T", bound=ErrataT)


def sort_erratas_by_source(erratas: list[T]) -> list[T]:
    def key(e: T) -> int:
        return SOURCE_ORDER[e.reason.details["from"]["source"]]

    return sorted(erratas, key=key)


def build_manage_errata_payload(
    user: str, reason: str, action: str, errata: Errata
) -> dict[str, Any]:
    return {"user": user, "reason": reason, "action": action, "errata": errata.asdict()}


def update_manage_errata_reason(me: ManageErrata, et: ErrataT) -> None:
    me.reason.details.update(et.reason.details)
    me.reason.details["original_message"] = et.reason.message


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
        cpe: str
        cve_ids: tuple[str, ...]

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

    if (action, source) == (CHANGE_ACTION_DISCARD, SOURCE_CPE_DISCRAD):
        result["reason"] = "by CPE discard"

    if (action, source) == (CHANGE_ACTION_DISCARD, SOURCE_PNC_DISCRAD):
        result["reason"] = "by PNC discard"

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
            result["match"]["cves"] = ep.cve_ids
        else:
            result["match"]["cve"] = ep.cvm.id
            result["match"]["cpe"] = pcm.pkg_cpe if pcm else ep.cvm.versions.cpe
            result["match"]["versions"] = {
                "version_start": ep.cvm.versions.version_start,
                "version_start_excluded": ep.cvm.versions.version_start_excluded,
                "version_end": ep.cvm.versions.version_end,
                "version_end_excluded": ep.cvm.versions.version_end_excluded,
            }

    if "cpe" in args or "cve_ids" in args:
        if "match" not in result:
            result["match"] = {}

        result["match"]["cpe"] = args.get("cpe", "")
        result["match"]["cve_ids"] = list(args.get("cve_ids", []))

    return result


def build_reason_string(et: ErrataT) -> str:
    message: list[str] = []

    reason = et.reason.details

    if isinstance(et, ErrataCreate):
        message = ["Create Errata on"]
    elif isinstance(et, ErrataUpdate):
        message = [f"Update Errata '{et.errata.id}' on"]
    else:
        message = [f"Discard or update Errata '{et.errata.id}' on"]

    if KEY_ACTION in reason:
        message.append(f"{reason[KEY_ACTION]}")
    if KEY_CPE in reason:
        # changes come from CPE manage
        cpe = reason[KEY_CPE]
        message.append(
            f"CPE '{cpe[KEY_CPE]}' for project '{cpe[KEY_PROJECT]}' [{cpe[KEY_STATE]}]"
        )
    elif KEY_PNC in reason:
        # changes come from PNC manage
        pnc = reason[KEY_PNC]
        message.append(
            f"mapping '{pnc[KEY_PACKAGE]}' for project '{pnc[KEY_PROJECT]}' [{pnc[KEY_STATE]}]"
        )
    else:
        pass

    if isinstance(et, (ErrataCreate, ErrataUpdate)):
        if isinstance(et.ep, ErrataPoint):
            message.append(f"[match CPE: {et.ep.cvm.versions.cpe}]")
        else:
            message.append(f"[changelog EVR: {et.ep.evr}]")

        message.extend(
            [
                "for package",
                f"{et.ep.task.name} {et.ep.task.version}-{et.ep.task.release}",
                f"[{et.ep.task.task_id}:{et.ep.task.subtask_id}] in '{et.ep.task.branch}'",
            ]
        )

    return " ".join(message)


def build_errata_create(
    ec: ErrataCreate, cve_ids: set[str], bdus_by_cve: dict[str, set[str]]
) -> Errata:
    references = []
    for cve_id in cve_ids:
        references.append(Reference(VULN_REFERENCE_TYPE, cve_id))
        for bdu_id in bdus_by_cve.get(cve_id, set()):
            references.append(Reference(VULN_REFERENCE_TYPE, bdu_id))

    references = sorted(references)

    errata = Errata(
        id=None,
        type=TASK_PACKAGE_ERRATA_TYPE,
        source=TASK_PACKAGE_ERRATA_SOURCE,
        created=DT_NEVER,
        updated=DT_NEVER,
        pkg_hash=ec.ep.task.hash,
        pkg_name=ec.ep.task.name,
        pkg_version=ec.ep.task.version,
        pkg_release=ec.ep.task.release,
        pkgset_name=ec.ep.task.branch,
        task_id=ec.ep.task.task_id,
        subtask_id=ec.ep.task.subtask_id,
        task_state=TASK_STATE_DONE,
        references=references,
        hash=0,
        is_discarded=False,
    )

    return errata


def build_errata_discard(
    ed: ErrataDiscard, cve_ids: set[str], bdus_by_cve: dict[str, set[str]]
) -> Errata:
    errata = ed.errata
    references = errata.references[:]
    linked_vulns = {r.link for r in references}

    # remove CVE and realted BDU from references
    for cve_id in cve_ids.intersection(linked_vulns):
        references.remove(Reference(VULN_REFERENCE_TYPE, cve_id))
        for bdu_id in bdus_by_cve.get(cve_id, set()).intersection(linked_vulns):
            try:
                references.remove(Reference(VULN_REFERENCE_TYPE, bdu_id))
            except ValueError:
                # skip repetitve related BDU removal
                pass

    errata = errata.update(references=sorted(references))
    errata = errata.update(hash=errata_hash(errata))

    return errata


def build_errata_update(
    eu: ErrataUpdate, cve_ids: set[str], bdus_by_cve: dict[str, set[str]]
) -> Errata:
    errata = eu.errata
    references = errata.references[:]
    linked_vulns = {r.link for r in references}

    # append new CVE and realted BDU references if not exists
    for cve_id in cve_ids.difference(linked_vulns):
        references.append(Reference(VULN_REFERENCE_TYPE, cve_id))
        for bdu_id in bdus_by_cve.get(cve_id, set()).difference(linked_vulns):
            references.append(Reference(VULN_REFERENCE_TYPE, bdu_id))

    errata = errata.update(references=sorted(references))
    errata = errata.update(hash=errata_hash(errata))

    return errata
