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

from typing import Any, NamedTuple, Union

from altrepodb_libs import (
    PackageCVEMatcher,
    PackageCveMatch,
    PackageCpePair,
    DatabaseConfig,
    convert_log_level,
)

from altrepo_api.libs.pagination import Paginator
from altrepo_api.libs.sorting import rich_sort
from altrepo_api.settings import namespace as settings

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.utils import make_tmp_table_name, get_real_ip

from .processing import ErrataBuilder, ErrataBuilderError
from .processing.base import (
    CPE,
    CpeRaw,
    CpeRecord,
    compare_pnc_records,
    cpe_record2pnc_record,
    uniq_pcm_records,
)
from .processing.helpers import cpe_transaction_rollback
from .tools.base import ChangeReason, ChangeSource, PncRecord, PncRecordType, UserInfo
from .tools.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_DISCARD,
    CHANGE_ACTION_UPDATE,
    DRY_RUN_KEY,
    KEY_ACTION,
    KEY_CPE,
    KEY_STATE,
    KEY_PROJECT,
    PNC_STATES,
    PNC_STATE_ACTIVE,
    PNC_STATE_INACTIVE,
    PNC_STATE_CANDIDATE,
)
from .tools.cpe_transaction import Transaction, PncType
from .tools.helpers.package import (
    get_related_packages_by_project_name,
    get_pkgs_branch_and_evr_by_hashes,
    store_pnc_records,
    store_pnc_change_records,
)
from .tools.utils import validate_action, validate_branch_with_tasks
from ..sql import sql

MATCHER_LOG_LEVEL = convert_log_level(settings.LOG_LEVEL)
# FIXME: collecting and returning packages' CVE matches info could be quite heavy
COLLECT_AND_RETURN_PCMS_DETAILS = False
RETUNRN_VULNERABLE_ONLY_PCMS = False
JOIN_TYPE_INNER = "INNER"
JOIN_TYPE_LEFT = "LEFT"
BRANCH_NONE = "none"


class CPECandidates(APIWorker):
    """Retrieves CPE candidates records."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        cpes: dict[tuple[str, str], Any] = {}

        all_candidates = self.args.get("all", False)
        limit = self.args.get("limit")
        page = self.args.get("page")

        sql = self.sql.get_cpes.format(
            cpe_branches=lut.repology_branches,
            pkg_name_conversion_clause="",
            cpe_states=(PNC_STATE_CANDIDATE,),
            join_type=JOIN_TYPE_LEFT if all_candidates else JOIN_TYPE_INNER,
        )

        response = self.send_sql_request(sql)
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"Error": "No CPE candidates found in DB"})

        for el in response:
            try:
                cpe_raw = CpeRaw(*el)

                branch = lut.repology_reverse_branch_map.get(
                    cpe_raw.repology_branch, [BRANCH_NONE]
                )[0]
                cpe = CPE(cpe_raw.cpe)
                cpe_s = str(cpe)

                if cpe.vendor == "*" or cpe.product == "*":
                    self.logger.info(f"Skip malformed CPE candidate: {el}")
                    continue

                if (cpe_s, cpe_raw.repology_name) not in cpes:
                    cpes[(cpe_s, cpe_raw.repology_name)] = {
                        "state": cpe_raw.state,
                        "packages": (
                            [{"name": cpe_raw.name, "branch": branch}]
                            if branch != BRANCH_NONE
                            else []
                        ),
                    }
                else:
                    cpes[(cpe_s, cpe_raw.repology_name)]["packages"].append(
                        {"name": cpe_raw.name, "branch": branch}
                    )
            except (TypeError, ValueError):
                self.logger.info(f"Failed to parse CPE from {el}")
                continue

        cpes_list = [{"cpe": k[0], "repology_name": k[1], **v} for k, v in cpes.items()]

        paginator = Paginator(cpes_list, limit)
        res = paginator.get_page(page)

        res = {
            "length": len(res),
            "cpes": res,
        }

        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )


class ManageCpe(APIWorker):
    """CPE records management handler."""

    def __init__(self, connection, payload, **kwargs):
        self.payload: dict[str, Any] = payload
        self.dry_run = kwargs.get(DRY_RUN_KEY, False)
        self.change_source = ChangeSource.AUTO
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.trx = Transaction(source=ChangeSource.MANUAL)
        # private fields
        self._branch: Union[str, None] = None
        self._package_name: Union[str, None] = None
        self._related_packages: list[str] = []
        self._related_cve_ids: list[str] = []
        self._packages_cve_matches: list[dict[str, Any]] = []
        # values set in self.check_params_xxx() call
        self.action: str
        self.reason: ChangeReason
        self.cpe: CpeRecord
        self.eb: ErrataBuilder
        super().__init__()

    def _valiadte_and_parse(self):
        """Validate and parse `self.payload' JSON contents."""

        # get package name from args if specified
        self._package_name = self.args.get("package_name", None)

        # build change reason object
        self.reason = ChangeReason(
            user=UserInfo(
                name=self.payload.get("user", ""),
                ip=get_real_ip(),
            ),
            message=self.payload.get("reason", ""),
            details={},
        )

        # inirtialize ErrataBuilder
        self.eb = ErrataBuilder(
            connection=self.conn,
            branches=lut.errata_manage_branches_with_tasks,
            reason=self.reason,
            transaction_id=self.trx.id,
            dry_run=self.dry_run,
            type=PncRecordType.CPE,
        )

        self.action = self.payload.get("action", "")

        if not self.reason.user.name:
            self.validation_results.append("User name should be specified")

        if not self.reason.message:
            self.validation_results.append("CPE change reason should be specified")

        if not validate_action(self.action):
            self.validation_results.append(
                f"CPE change action '{self.action}' not supported"
            )

        cpe: dict[str, str] = self.payload.get("cpe", {})
        if not cpe:
            self.validation_results.append("No CPE records object found")
            return
        else:
            try:
                cpe_ = CpeRecord(
                    cpe=CPE(cpe["cpe"]),
                    state=cpe["state"],
                    project_name=cpe["project_name"],
                )

                if not cpe_.project_name or not cpe_.state:
                    raise ValueError("Required fields values are empty")

                if cpe_.state not in PNC_STATES:
                    raise ValueError(f"Invalid CPE record state: {cpe_.state}")

                self.cpe = cpe_
                # store CPE contents to `reason` object
                self.reason.details[KEY_CPE] = {
                    KEY_CPE: repr(self.cpe.cpe),
                    KEY_STATE: self.cpe.state,
                    KEY_PROJECT: self.cpe.project_name,
                }
                self.reason.details[KEY_ACTION] = self.action
            except Exception as e:
                self.validation_results.append(
                    f"Failed to parse CPE record object {cpe}: {e}"
                )
                return

    def _collect_packages_cve_match_info(
        self, pcms: list[PackageCveMatch]
    ) -> list[dict[str, Any]]:
        pcm_info_records = uniq_pcm_records(
            pcms, vulnerable_only=RETUNRN_VULNERABLE_ONLY_PCMS
        )

        pkgs_info = get_pkgs_branch_and_evr_by_hashes(self, {m.pkg_hash for m in pcms})

        for p in pcm_info_records:
            p.update(**pkgs_info.get(p["pkg_hash"], {}))

        return pcm_info_records

    def _get_pkgs_cve_matches_by_hashes(
        self, match_hashes: list[int]
    ) -> list[PackageCveMatch]:
        self.status = False

        tmp_table = make_tmp_table_name("pkgs_match_hashes")

        response = self.send_sql_request(
            self.sql.get_pkg_cve_matches_by_hashes.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("key_hash", "UInt64")],
                    "data": [{"key_hash": h} for h in match_hashes],
                },
            ],
        )
        if not self.sql_status or not response:
            return []

        self.status = True
        return [PackageCveMatch(*el) for el in response]

    def _check_package_name_is_consistent_with_db(self) -> bool:
        if not self._package_name:
            return True

        if self._package_name not in self._related_packages:
            self.store_error(
                {
                    "message": "Given package name not found in related packages",
                    "package_name": self._package_name,
                    "related_packages": self._related_packages,
                },
                self.LL.WARNING,
                409,
            )
            return False

        if len(self._related_packages) > 1:
            self.store_error(
                {
                    "message": "Multiple packages are affected by given CPE match record changes, but one was specified",
                    "package_name": self._package_name,
                    "related_packages": self._related_packages,
                },
                self.LL.WARNING,
                409,
            )
            return False

        return True

    def _commit_or_rollback(self):
        status = False
        errors = []

        class CommitError(Exception):
            pass

        try:
            # store Erratas' changes
            try:
                self.eb.commit()
            except ErrataBuilderError:
                self.logger.error("Failed to build erratas")
                errors.append(self.eb.error)
                raise CommitError
            # store PNC records changes
            if not self.dry_run:
                # XXX: data save order is important here!
                # 1. store `PncChangeHistory` records
                store_pnc_change_records(self, self.trx.pnc_change_records)
                if not self.sql_status:
                    errors.append(self.error)
                    raise CommitError
                # 2. stor `PackagesNameConversion` records
                store_pnc_records(self, self.trx.pnc_records)
                if not self.sql_status:
                    errors.append(self.error)
                    raise CommitError
        except CommitError:
            status = self.eb.rollback()
            if not status:
                errors.extend(self.eb.rollback_errors)
            if not self.dry_run:
                status = self.trx.rollback(cpe_transaction_rollback(self))
                if not status:
                    errors.append(self.error)
        else:
            # happy path
            self.logger.info(
                f"All changes comitted to DB for transaction {self.trx.id}"
            )
            return {
                "user": self.reason.user.name,
                "action": self.action,
                "reason": self.reason.message,
                "message": "OK",
                "cpe": self.cpe.asdict(),
                "package_name": self._package_name or "",
                "related_packages": self._related_packages,
                "related_cve_ids": self._related_cve_ids,
                "cpe_records": [r.asdict() for r in self.trx.pnc_records],
                "cpe_change_records": [r.asdict() for r in self.trx.pnc_change_records],
                "errata_records": self.eb.errata_records,
                "errata_change_records": self.eb.errata_change_records,
                "packages_cve_matches": self._packages_cve_matches,
            }, 200

        # errors occured during rollback
        return self.store_error(
            {
                "message": "Errors occured while commiting changes to DB",
                "errors": errors,
            },
            self.LL.CRITICAL,
            500,
        )

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        # parse package name and branch form request args if exists
        branch = self.args.get("branch", None)
        if branch is not None and not validate_branch_with_tasks(branch):
            self.validation_results.append(f"Invalid branch: {self.args['branch']}")
            return False

        self._branch = branch
        self._package_name = self.args.get("package_name", None)

        return True

    def check_params_post(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_CREATE:
            self.validation_results.append("Change action validation error")

        if self.cpe.state in (PNC_STATE_INACTIVE, PNC_STATE_CANDIDATE):
            self.validation_results.append(
                f"Invalid CPE match record state: {self.cpe.asdict()}"
            )

        if self.validation_results != []:
            return False
        return True

    def check_params_put(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_UPDATE:
            self.validation_results.append("Change action validation error")

        if self.cpe.state != PNC_STATE_ACTIVE:
            self.validation_results.append(
                f"Invalid CPE match record state: {self.cpe.asdict()}"
            )

        if self.validation_results != []:
            return False
        return True

    def check_params_delete(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_DISCARD:
            self.validation_results.append("Change action validation error")

        if self.cpe.state != PNC_STATE_INACTIVE:
            self.validation_results.append(
                f"Invalid CPE match record state: {self.cpe.asdict()}"
            )

        if self.validation_results != []:
            return False
        return True

    def get(self):
        """Get CPE records, active and candidate, by package name
        and branch (optional)."""

        cpes: dict[tuple[str, str], Any] = {}

        if self._branch is None:
            cpe_branches = lut.repology_branches
        else:
            cpe_branches = (lut.repology_branch_map[self._branch],)

        # get last CPE match states for specific package name
        response = self.send_sql_request(
            self.sql.get_cpes.format(
                cpe_branches=cpe_branches,
                pkg_name_conversion_clause=f"AND alt_name = '{self._package_name}'",
                cpe_states=PNC_STATES,
                join_type=JOIN_TYPE_INNER,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "Error": f"No CPE records found in DB for package '{self._package_name}'"
                }
            )

        for el in response:
            try:
                cpe_raw = CpeRaw(*el)

                _branch = lut.repology_reverse_branch_map[cpe_raw.repology_branch][0]
                cpe = CPE(cpe_raw.cpe)
                cpe_s = str(cpe)

                if cpe.vendor == "*" or cpe.product == "*":
                    self.logger.info(f"Skip malformed CPE candidate: {el}")
                    continue

                if (cpe_s, cpe_raw.repology_name) not in cpes:
                    cpes[(cpe_s, cpe_raw.repology_name)] = {
                        "state": cpe_raw.state,
                        "packages": [{"name": cpe_raw.name, "branch": _branch}],
                    }
                else:
                    cpes[(cpe_s, cpe_raw.repology_name)]["packages"].append(
                        {"name": cpe_raw.name, "branch": _branch}
                    )
            except (TypeError, ValueError):
                self.logger.info(f"Failed to parse CPE from {el}")
                continue

        return {
            "length": len(cpes),
            "name": self._package_name or "",
            "branch": self._branch or "",
            "cpes": [
                {"cpe": k[0], "repology_name": k[1], **v} for k, v in cpes.items()
            ],
        }, 200

    def post(self):
        """Handles CPE records create.
        Returns:
            - 200 (OK) if CPE record created successfully
            - 400 (Bad request) on paload validation errors
            - 409 (Conflict) if such CPE record exists already in DB
        """
        # get CPE match records by `project_name`
        db_cpes: dict[str, list[PncRecord]] = {}
        _tmp_table = "_project_names_tmp_table"
        response = self.send_sql_request(
            self.sql.get_cpes_by_project_names.format(
                tmp_table=_tmp_table, cpe_states=PNC_STATES
            ),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("project_name", "String"),
                    ],
                    "data": [{"project_name": self.cpe.project_name}],
                },
            ],
        )
        if not self.sql_status:
            return self.error
        if response:
            for p in (PncRecord(*el) for el in response):
                db_cpes.setdefault(p.pkg_name, []).append(p)

        pncr = cpe_record2pnc_record(self.cpe)

        # check if any records already exists in DB
        if db_cpes:
            pncr = cpe_record2pnc_record(self.cpe)
            for p in db_cpes.get(self.cpe.project_name, []):
                if compare_pnc_records(pncr, p, include_state=False):
                    return self.store_error(
                        {
                            "message": f"CPE record already exists in DB: {p}.",
                        },
                        http_code=409,
                    )

        # check if there is any packages that affected by added CPE records in branches
        self._related_packages = get_related_packages_by_project_name(
            self, [self.cpe.project_name]
        )
        if not self.status:
            return self.error

        # create and store new CPE match records
        self.trx.register_pnc_create(pnc=pncr, pnc_type=PncType.CPE)
        self.trx.commit(self.reason)

        # check if `package_name` was specified and consistent with DB contents
        if not self._check_package_name_is_consistent_with_db():
            return self.error

        if self._related_packages:
            # update PackagesCveMatch table
            pkg_cpe_pairs = [
                PackageCpePair(name=self.cpe.project_name, cpe=str(self.cpe.cpe))
            ]
            matcher = PackageCVEMatcher(
                db_config=DatabaseConfig(
                    host=settings.DATABASE_HOST,
                    port=settings.DATABASE_PORT,
                    dbname=settings.DATABASE_NAME,
                    user=settings.DATABASE_USER,
                    password=settings.DATABASE_PASS,
                ),
                log_level=MATCHER_LOG_LEVEL,
                sql_patch={"tmp_db_name": settings.TMP_DATABASE_NAME},
            )
            if self._package_name:
                matcher.match_cpe_add(pkg_cpe_pairs, package_name=self._package_name)
            else:
                matcher.match_cpe_add(pkg_cpe_pairs)

            pcms = matcher.packages_cve_matches
            # XXX: if all packages' CVE matches already loaded use hashes from matcher
            if not pcms and matcher.packages_cve_match_hashes:
                self.logger.info(
                    "Got no new packages' CVE matches, use existing hashes"
                )
                pcms = self._get_pkgs_cve_matches_by_hashes(
                    matcher.packages_cve_match_hashes
                )
                if not self.status:
                    return self.error

            self._related_cve_ids = sorted({m.vuln_id for m in pcms})

            if not self.dry_run:
                matcher.store()

            del matcher

            # collect packages info from latest branch states
            if COLLECT_AND_RETURN_PCMS_DETAILS:
                self._packages_cve_matches = self._collect_packages_cve_match_info(pcms)

            # XXX: update or create erratas
            try:
                self.eb.build_erratas_on_add(pcms, self._package_name)
            except ErrataBuilderError:
                self.logger.error("Failed to build erratas")
                return self.eb.error

        return self._commit_or_rollback()

    def put(self):
        """Handles CPE record update.
        Returns:
            - 200 (OK) if CPE record was updated or no changes found to be made
            - 400 (Bad request) on paload validation errors
            - 404 (Not found) if CPE record does not exists
        """
        # get CPE match records by `project_name`
        db_cpes: dict[str, list[PncRecord]] = {}
        _tmp_table = "_project_names_tmp_table"
        response = self.send_sql_request(
            self.sql.get_cpes_by_project_names.format(
                tmp_table=_tmp_table, cpe_states=PNC_STATES
            ),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("project_name", "String"),
                    ],
                    "data": [{"project_name": self.cpe.project_name}],
                },
            ],
        )
        if not self.sql_status:
            return self.error
        if response:
            for p in (PncRecord(*el) for el in response):
                db_cpes.setdefault(p.pkg_name, []).append(p)

        pncr = cpe_record2pnc_record(self.cpe)

        # check if any records are doesn't exists in DB
        if not db_cpes:
            return self.store_error(
                {
                    "message": "no corresponding CPE match records found in DB to be updated"
                },
                http_code=404,
            )
        else:
            not_found_in_db = True
            for p in db_cpes.get(self.cpe.project_name, []):
                if compare_pnc_records(pncr, p, include_state=False):
                    not_found_in_db = False
                    break

            if not_found_in_db:
                return self.store_error(
                    {
                        "message": f"CPE match record not found in DB to be updated: {self.cpe}.",
                    },
                    http_code=404,
                )

        # check if any updates are ever exists
        for p in db_cpes.get(self.cpe.project_name, []):
            if compare_pnc_records(pncr, p, include_state=True):
                return {
                    "user": self.reason.user.name,
                    "action": self.action,
                    "reason": self.reason.message,
                    "message": "No changes found to be stored to DB",
                    "cpe": self.cpe.asdict(),
                    "package_name": self._package_name or "",
                    "related_packages": self._related_packages,
                    "related_cve_ids": self._related_cve_ids,
                    "cpe_records": [],
                    "cpe_change_records": [],
                    "errata_records": [],
                    "errata_change_records": [],
                    "packages_cve_matches": [],
                }, 200

        # check if there is any packages that affected by added CPE records in branches
        self._related_packages = get_related_packages_by_project_name(
            self, [self.cpe.project_name]
        )
        if not self.status:
            return self.error

        # create and store new CPE match records
        self.trx.register_pnc_update(pnc=pncr, pnc_type=PncType.CPE)
        self.trx.commit(self.reason)

        # FIXME: ignore `package_name` argument here
        # # check if `package_name` was specified and consistent with DB contents
        # if not self._check_package_name_is_consistent_with_db():
        #     return self.error
        if self._package_name:
            return self.store_error(
                {
                    "message": "'package_name' argument not supported here",
                    "package_name": self._package_name,
                },
                self.LL.WARNING,
                400,
            )

        if self._related_packages:
            # update PackagesCveMatch table
            pkg_cpe_pairs = [
                PackageCpePair(name=self.cpe.project_name, cpe=str(self.cpe.cpe))
            ]
            matcher = PackageCVEMatcher(
                db_config=DatabaseConfig(
                    host=settings.DATABASE_HOST,
                    port=settings.DATABASE_PORT,
                    dbname=settings.DATABASE_NAME,
                    user=settings.DATABASE_USER,
                    password=settings.DATABASE_PASS,
                ),
                log_level=MATCHER_LOG_LEVEL,
                sql_patch={"tmp_db_name": settings.TMP_DATABASE_NAME},
            )
            # FIXME: ignore `package_name` argument here
            # if self._package_name:
            #     matcher.match_cpe_add(pkg_cpe_pairs, package_name=self._package_name)
            # else:
            matcher.match_cpe_add(pkg_cpe_pairs)

            pcms = matcher.packages_cve_matches
            # XXX: if all packages' CVE matches already loaded use hashes from matcher
            if not pcms and matcher.packages_cve_match_hashes:
                self.logger.info(
                    "Got no new packages' CVE matches, use existing hashes"
                )
                pcms = self._get_pkgs_cve_matches_by_hashes(
                    matcher.packages_cve_match_hashes
                )
                if not self.status:
                    return self.error

            self._related_cve_ids = sorted({m.vuln_id for m in pcms})

            if not self.dry_run:
                matcher.store()

            del matcher

            # collect packages info from latest branch states
            if COLLECT_AND_RETURN_PCMS_DETAILS:
                self._packages_cve_matches = self._collect_packages_cve_match_info(pcms)

            # XXX: update or create erratas
            try:
                self.eb.build_erratas_on_add(pcms, self._package_name)
            except ErrataBuilderError:
                self.logger.error("Failed to build erratas")
                return self.eb.error

        return self._commit_or_rollback()

    def delete(self):
        """Handles CPE record discard.
        Returns:
            - 200 (OK) if CPE record discarded successfully
            - 400 (Bad request) on paload validation errors
            - 404 (Not found) if CPE record is discarded already or does not exists
            - 409 (Conflict) if CPE state in 'active'
        """

        # get CPE match records by `project_name`
        db_cpes: dict[str, list[PncRecord]] = {}
        _tmp_table = "_project_names_tmp_table"
        response = self.send_sql_request(
            self.sql.get_cpes_by_project_names.format(
                tmp_table=_tmp_table,
                cpe_states=(PNC_STATE_ACTIVE, PNC_STATE_CANDIDATE, PNC_STATE_INACTIVE),
            ),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("project_name", "String"),
                    ],
                    "data": [{"project_name": self.cpe.project_name}],
                },
            ],
        )
        if not self.sql_status:
            return self.error
        if response:
            for p in (PncRecord(*el) for el in response):
                db_cpes.setdefault(p.pkg_name, []).append(p)

        pncr = cpe_record2pnc_record(self.cpe)
        db_cpe: Union[CpeRecord, None] = None

        # check if any records are doesn't exists in DB
        if not db_cpes:
            return self.store_error(
                {
                    "message": "no corresponding CPE match records found in DB to be updated"
                },
                http_code=404,
            )
        else:
            for p in db_cpes.get(self.cpe.project_name, []):
                if compare_pnc_records(pncr, p, include_state=False):
                    db_cpe = CpeRecord(
                        cpe=CPE(p.pnc_result),
                        state=p.pnc_state,
                        project_name=p.pkg_name,
                    )
                    break

            if not db_cpe:
                return self.store_error(
                    {
                        "message": f"CPE match record not found in DB to be updated: {self.cpe}.",
                    },
                    http_code=404,
                )

        # check if any updates are ever exists
        for p in db_cpes.get(self.cpe.project_name, []):
            if compare_pnc_records(pncr, p, include_state=True):
                return {
                    "user": self.reason.user.name,
                    "action": self.action,
                    "reason": self.reason.message,
                    "message": "No changes found to be stored to DB",
                    "cpe": self.cpe.asdict(),
                    "package_name": self._package_name or "",
                    "related_packages": self._related_packages,
                    "related_cve_ids": self._related_cve_ids,
                    "cpe_records": [],
                    "cpe_change_records": [],
                    "errata_records": [],
                    "errata_change_records": [],
                    "packages_cve_matches": [],
                }, 200

        # create and store new CPE match records
        self.trx.register_pnc_discard(pnc=pncr, pnc_type=PncType.CPE)
        self.trx.commit(self.reason)

        # if discarded CPE record is `candidate` state just store PNC record
        if db_cpe.state == PNC_STATE_CANDIDATE:
            return self._commit_or_rollback()

        # check if there is any packages that affected by added CPE records in branches
        self._related_packages = get_related_packages_by_project_name(
            self, [self.cpe.project_name]
        )
        if not self.status:
            return self.error

        # check if `package_name` was specified and consistent with DB contents
        if not self._check_package_name_is_consistent_with_db():
            return self.error

        if self._related_packages:
            # update PackagesCveMatch table
            pkg_cpe_pairs = [
                PackageCpePair(name=self.cpe.project_name, cpe=str(self.cpe.cpe))
            ]
            matcher = PackageCVEMatcher(
                db_config=DatabaseConfig(
                    host=settings.DATABASE_HOST,
                    port=settings.DATABASE_PORT,
                    dbname=settings.DATABASE_NAME,
                    user=settings.DATABASE_USER,
                    password=settings.DATABASE_PASS,
                ),
                log_level=MATCHER_LOG_LEVEL,
                sql_patch={"tmp_db_name": settings.TMP_DATABASE_NAME},
            )
            if self._package_name:
                matcher.match_cpe_delete(pkg_cpe_pairs, package_name=self._package_name)
            else:
                matcher.match_cpe_delete(pkg_cpe_pairs)

            pcms = matcher.packages_cve_matches
            # XXX: if all packages' CVE matches already loaded use hashes from matcher
            if not pcms and matcher.packages_cve_match_hashes:
                self.logger.info(
                    "Got no new packages' CVE matches, use existing hashes"
                )
                pcms = self._get_pkgs_cve_matches_by_hashes(
                    matcher.packages_cve_match_hashes
                )
                if not self.status:
                    return self.error

            self._related_cve_ids = sorted({m.vuln_id for m in pcms})

            if not self.dry_run:
                matcher.store()

            del matcher

            # collect packages info from latest branch states
            if COLLECT_AND_RETURN_PCMS_DETAILS:
                self._packages_cve_matches = self._collect_packages_cve_match_info(pcms)

            # XXX: update or discard erratas
            try:
                self.eb.build_erratas_on_delete(pcms, self._package_name)
            except ErrataBuilderError:
                self.logger.error("Failed to build erratas")
                return self.eb.error

        return self._commit_or_rollback()


class CPEListArgs(NamedTuple):
    input: Union[str, None]
    is_discarded: bool
    limit: Union[int, None]
    page: Union[int, None]
    sort: Union[list[str], None]


class CPEList(APIWorker):
    """Retrieves CPE records."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = CPEListArgs(**kwargs)
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    @property
    def _where_condition(self) -> str:
        if self.args.input.startswith("CVE-"):  # type: ignore
            response = self.send_sql_request(
                self.sql.get_cpes_by_vulns.format(cves=[self.args.input])
            )
            return f"WHERE cpe IN {[el[0] for el in response]}"

        return (
            f"WHERE pkg_name ILIKE '%{self.args.input}%' "
            f"OR repology_name ILIKE '%{self.args.input}%' "
            f"OR cpe ILIKE '%{self.args.input}%'"
        )

    def get(self):
        cpes: dict[tuple[str, str], Any] = {}
        state = "WHERE state = 'inactive'" if self.args.is_discarded else ""

        response = self.send_sql_request(
            self.sql.find_cpe.format(
                where=self._where_condition if self.args.input else "",
                state=state,
                pnc_branches=lut.repology_branches,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args._asdict(),
                }
            )

        for el in response:
            try:
                cpe_raw = CpeRaw(*el)

                branch = lut.repology_reverse_branch_map[cpe_raw.repology_branch][0]
                cpe = CPE(cpe_raw.cpe)
                cpe_s = str(cpe)

                if cpe.vendor == "*" or cpe.product == "*":
                    self.logger.info(f"Skip malformed CPE candidate: {el}")
                    continue

                if (cpe_s, cpe_raw.repology_name) not in cpes:
                    cpes[(cpe_s, cpe_raw.repology_name)] = {
                        "state": cpe_raw.state,
                        "packages": [{"name": cpe_raw.name, "branch": branch}],
                    }
                else:
                    cpes[(cpe_s, cpe_raw.repology_name)]["packages"].append(
                        {"name": cpe_raw.name, "branch": branch}
                    )
            except (TypeError, ValueError):
                self.logger.info(f"Failed to parse CPE from {el}")
                continue

        result = [{"cpe": k[0], "repology_name": k[1], **v} for k, v in cpes.items()]
        if self.args.sort:
            result = rich_sort(result, self.args.sort)

        paginator = Paginator(result, self.args.limit)
        page_obj = paginator.get_page(self.args.page)

        res: dict[str, Any] = {
            "request_args": self.args._asdict(),
            "length": len(page_obj),
            "cpes": page_obj,
        }

        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )
