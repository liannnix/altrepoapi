# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

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

from altrepodb_libs import (
    PackageCVEMatcher,
    PackageCveMatch,
    PackageCpePair,
    DatabaseConfig,
    convert_log_level,
)

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.libs.pagination import Paginator
from altrepo_api.libs.sorting import rich_sort
from altrepo_api.settings import namespace as settings
from altrepo_api.utils import make_tmp_table_name, get_real_ip

from .processing import ErrataBuilder, ErrataBuilderError
from .processing.base import compare_pnc_records, uniq_pcm_records
from .processing.helpers import cpe_transaction_rollback
from .tools.base import (
    ChangeSource,
    ChangeReason,
    PncListElement,
    PncPackage,
    PncRecord,
    PncRecordType,
    UserInfo,
)
from .tools.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_DISCARD,
    CHANGE_ACTION_UPDATE,
    CHANGE_SOURCE_MANUAL,
    DRY_RUN_KEY,
    KEY_ACTION,
    KEY_STATE,
    KEY_PNC,
    KEY_PACKAGE,
    KEY_PROJECT,
    PNC_STATES,
    PNC_STATE_ACTIVE,
    PNC_STATE_INACTIVE,
    PNC_SOURCES,
)
from .tools.cpe_transaction import Transaction, PncType
from .tools.helpers.package import (
    store_pnc_records,
    store_pnc_change_records,
    get_pkgs_branch_and_evr_by_hashes,
)
from .tools.helpers.pnc import (
    get_cpes_by_projects,
    get_pncs_by_package,
    get_pkgs_cve_matches_by_hashes,
)
from .tools.utils import validate_action
from ..sql import sql

MATCHER_LOG_LEVEL = convert_log_level(settings.LOG_LEVEL)


class ManagePnc(APIWorker):
    def __init__(self, connection, payload, **kwargs):
        self.payload: dict[str, Any] = payload
        self.dry_run = kwargs.get(DRY_RUN_KEY, False)
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.trx = Transaction(source=ChangeSource.MANUAL)
        self._related_cve_ids: list[str] = []
        # values set in self.check_params_xxx() call
        self.action: str
        self.eb: ErrataBuilder
        self.reason: ChangeReason
        self.pncs: list[PncRecord]
        super().__init__()

    def _valiadte_and_parse(self):
        """Validate and parse `self.payload' JSON contents."""

        self.reason = ChangeReason(
            actor=UserInfo(
                name=self.payload.get("user", ""),
                ip=get_real_ip(),
            ),
            message=self.payload.get("reason", ""),
            details={},
        )

        self.action = self.payload.get("action", "")

        if not self.reason.actor.name:
            self.validation_results.append("User name should be specified")

        if not self.reason.message:
            self.validation_results.append("PNC change reason should be specified")

        if not validate_action(self.action):
            self.validation_results.append(
                f"PNC change action '{self.action}' not supported"
            )

        self.pncs = []
        pnc: dict[str, str] = self.payload.get("pnc", {})
        if not pnc:
            self.validation_results.append("No PNC record object found")
            return
        else:
            try:
                package_name = pnc["package_name"]
                project_name = pnc["project_name"]
                pnc_state = pnc["state"]
                pnc_source = pnc["source"]

                if pnc_state not in PNC_STATES:
                    raise ValueError(f"Invalid PNC record state: {pnc_state}")

                if pnc_source not in PNC_SOURCES:
                    raise ValueError(f"Invalid PNC record source: {pnc_source}")

                if not (package_name and project_name):
                    raise ValueError("Required fields values are empty")

                for branch in lut.repology_branches:
                    self.pncs.append(
                        PncRecord(
                            pkg_name=package_name,
                            pnc_result=project_name,
                            pnc_state=pnc_state,
                            pnc_type=branch,
                            pnc_source=pnc_source,
                        )
                    )

                # store change source
                if pnc_source == CHANGE_SOURCE_MANUAL:
                    self.trx._source = ChangeSource.MANUAL
                else:
                    self.trx._source = ChangeSource.AUTO

                # store PNC contents to `reason` object
                self.reason.details[KEY_PNC] = {
                    KEY_STATE: pnc_state,
                    KEY_PACKAGE: package_name,
                    KEY_PROJECT: project_name,
                }
                self.reason.details[KEY_ACTION] = self.action
            except Exception as e:
                self.validation_results.append(
                    f"Failed to parse PNC record object {pnc}: {e}"
                )
                return

        # inirtialize ErrataBuilder
        self.eb = ErrataBuilder(
            connection=self.conn,
            branches=lut.errata_manage_branches_with_tasks,
            reason=self.reason,
            transaction_id=self.trx.id,
            dry_run=self.dry_run,
            type=PncRecordType.PNC,
        )

    def _collect_packages_cve_match_info(
        self, pcms: list[PackageCveMatch]
    ) -> list[dict[str, Any]]:
        pcm_info_records = uniq_pcm_records(pcms, vulnerable_only=False)

        pkgs_info = get_pkgs_branch_and_evr_by_hashes(self, {m.pkg_hash for m in pcms})

        for p in pcm_info_records:
            p.update(**pkgs_info.get(p["pkg_hash"], {}))

        return pcm_info_records

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
            status = self.trx.rollback(cpe_transaction_rollback(self))
            if not status:
                errors.append(self.error)
        else:
            # happy path
            self.logger.info(
                f"All changes comitted to DB for transaction {self.trx.id}"
            )
            return {
                "user": self.reason.actor.name,
                "action": self.action,
                "reason": self.reason.message,
                "message": "OK",
                "pnc_records": [r.asdict() for r in self.trx.pnc_records],
                "pnc_change_records": [r.asdict() for r in self.trx.pnc_change_records],
                "related_cve_ids": self._related_cve_ids,
                "errata_records": self.eb.errata_records,
                "errata_change_records": self.eb.errata_change_records,
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
        pkg_name = self.args.get("package_name", None)
        proj_name = self.args.get("project_name", None)

        if not pkg_name and not proj_name:
            self.validation_results.append(
                "At least one of 'package_name', 'project_name' arguments should be specified"
            )
            return False

        return True

    def check_params_post(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_CREATE:
            self.validation_results.append("Change action validation error")

        for pnc in self.pncs:
            if pnc.pnc_state != PNC_STATE_ACTIVE:
                self.validation_results.append(
                    f"Invalid PNC record state: {pnc.asdict()}"
                )
                break

        if self.validation_results != []:
            return False
        return True

    def check_params_put(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_UPDATE:
            self.validation_results.append("Change action validation error")

        for pnc in self.pncs:
            if pnc.pnc_state != PNC_STATE_ACTIVE:
                self.validation_results.append(
                    f"Invalid PNC record state: {pnc.asdict()}"
                )
                break

        if self.validation_results != []:
            return False
        return True

    def check_params_delete(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_DISCARD:
            self.validation_results.append("Change action validation error")

        for pnc in self.pncs:
            if pnc.pnc_state != PNC_STATE_INACTIVE:
                self.validation_results.append(
                    f"Invalid PNC record state: {pnc.asdict()}"
                )
                break

        if self.validation_results != []:
            return False
        return True

    def get(self):
        """Get package to project mapping records, by package name, project name or
        record state if specified."""

        pnc_records: list[PncRecord] = []

        pkg_name = self.args.get("package_name")
        proj_name = self.args.get("project_name")

        state = self.args.get("state")
        if state == "all":
            state = None

        # build where clause for PNC records gathering request
        where_conditions = [f"WHERE type IN {lut.repology_branches}"]

        if pkg_name:
            where_conditions.append(f"name = '{pkg_name}'")
        if proj_name:
            where_conditions.append(f"result = '{proj_name}'")
        if state:
            where_conditions.append(f"state = '{state}'")

        where_clause = " AND ".join(where_conditions)

        # get PNC records from DB
        response = self.send_sql_request(
            self.sql.get_pnc_records.format(where_clause=where_clause)
        )
        if not self.sql_status:
            return self.error

        pnc_records = [PncRecord(*el) for el in response]

        if not pnc_records:
            return self.store_error(
                {"message": f"No data found in DB for {self.args}"}, http_code=404
            )

        return {
            "request_args": self.args,
            "pncs": [r.asdict() for r in pnc_records],
        }, 200

    def post(self):
        """Handles package to project mapping PNC records create.
        Returns:
            - 200 (OK) if PNC record created successfully
            - 400 (Bad request) on paload validation errors
            - 409 (Conflict) if such PNC record exists already in DB
        """

        package_name = self.pncs[0].pkg_name
        project_name = self.pncs[0].pnc_result

        # get existing PNC records using package and project names
        pncs_by_package = get_pncs_by_package(self, package_name, (PNC_STATE_ACTIVE,))
        if not self.status:
            return self.error

        # check if new PNC records is consistent with DB contents
        for pnc in self.pncs:
            for pnc_db in pncs_by_package:
                # 1. check if PNC record already exists in DB
                if compare_pnc_records(pnc, pnc_db, include_state=True):
                    return self.store_error(
                        {
                            "message": f"PNC record already exists in DB: {pnc_db}.",
                        },
                        http_code=409,
                    )
                # 2. check if package already mapped to another project
                if (pnc.pkg_name, pnc.pnc_type) == (
                    pnc_db.pkg_name,
                    pnc_db.pnc_type,
                ) and pnc.pnc_result != pnc_db.pnc_result:
                    return self.store_error(
                        {
                            "message": (
                                f"Package '{pnc.pkg_name}' is already mapped "
                                f"to another project: '{pnc_db.pnc_result}'"
                            ),
                        },
                        http_code=409,
                    )
            # add new PNC records to transaction
            self.trx.register_pnc_create(pnc=pnc, pnc_type=PncType.NAME)

        # check if new PNC record' project exists in DB
        related_cpes = get_cpes_by_projects(
            self, (project_name,), (PNC_STATE_ACTIVE,)
        ).get(project_name, [])
        if not self.status:
            return self.error

        self.trx.commit(self.reason)

        # changes has no related CPE records
        if not related_cpes:
            return self._commit_or_rollback()

        # find and build Errata changes
        pkg_cpe_pairs = [
            PackageCpePair(name=project_name, cpe=r.pnc_result) for r in related_cpes
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
        )
        matcher.match_pnc_add(pkg_cpe_pairs, package_name=package_name)

        pcms = matcher.packages_cve_matches
        # XXX: if all packages' CVE matches already loaded use hashes from matcher
        if not pcms and matcher.packages_cve_match_hashes:
            self.logger.info("Got no new packages' CVE matches, use existing hashes")
            pcms = get_pkgs_cve_matches_by_hashes(
                self, matcher.packages_cve_match_hashes
            )
            if not self.status:
                return self.error

        self._related_cve_ids = sorted({m.vuln_id for m in pcms})

        if not self.dry_run:
            matcher.store()

        del matcher

        # collect packages info from latest branch states
        self._packages_cve_matches = self._collect_packages_cve_match_info(pcms)

        # XXX: update or create erratas
        try:
            self.eb.build_erratas_on_add(pcms, package_name)
        except ErrataBuilderError:
            self.logger.error("Failed to build erratas")
            return self.eb.error

        return self._commit_or_rollback()

    def put(self):
        return "OK", 200

    def delete(self):
        """Handles package to project mapping PNC records discard.
        Returns:
            - 200 (OK) if PNC record discarded successfully
            - 400 (Bad request) on paload validation errors
            - 409 (Conflict) if such PNC record exists already in DB
        """

        package_name = self.pncs[0].pkg_name
        project_name = self.pncs[0].pnc_result

        # get existing PNC records using package and project names
        pncs_by_package = get_pncs_by_package(self, package_name, (PNC_STATE_INACTIVE,))
        if not self.status:
            return self.error

        # check if new PNC records is consistent with DB contents
        for pnc in self.pncs:
            for pnc_db in pncs_by_package:
                # 1. check if PNC record already exists in DB
                if compare_pnc_records(pnc, pnc_db, include_state=True):
                    return self.store_error(
                        {
                            "message": f"PNC record already exists in DB: {pnc_db}.",
                        },
                        http_code=409,
                    )
            # add new PNC records to transaction
            self.trx.register_pnc_discard(pnc=pnc, pnc_type=PncType.NAME)

        # check if new PNC record' project exists in DB
        related_cpes = get_cpes_by_projects(
            self, (project_name,), (PNC_STATE_ACTIVE,)
        ).get(project_name, [])
        if not self.status:
            return self.error

        self.trx.commit(self.reason)

        # changes has no related CPE records
        if not related_cpes:
            return self._commit_or_rollback()

        # find and build Errata changes
        pkg_cpe_pairs = [
            PackageCpePair(name=project_name, cpe=r.pnc_result) for r in related_cpes
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
        )
        matcher.match_pnc_delete(pkg_cpe_pairs, package_name=package_name)

        pcms = matcher.packages_cve_matches
        # XXX: if all packages' CVE matches already loaded use hashes from matcher
        if not pcms and matcher.packages_cve_match_hashes:
            self.logger.info("Got no new packages' CVE matches, use existing hashes")
            pcms = get_pkgs_cve_matches_by_hashes(
                self, matcher.packages_cve_match_hashes
            )
            if not self.status:
                return self.error

        self._related_cve_ids = sorted({m.vuln_id for m in pcms})

        if not self.dry_run:
            matcher.store()

        del matcher

        # collect packages info from latest branch states
        self._packages_cve_matches = self._collect_packages_cve_match_info(pcms)

        # XXX: update or create erratas
        try:
            self.eb.build_erratas_on_delete(pcms, package_name)
        except ErrataBuilderError:
            self.logger.error("Failed to build erratas")
            return self.eb.error

        return self._commit_or_rollback()


class PncList(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        branch = self.args.get("branch", None)

        if branch is not None and branch not in lut.repology_branch_map:
            self.validation_results.append(f"Invalid branch: {branch}")
            return False

        return True

    def _get_cpes(self, pncs: list[dict[str, Any]]):
        self.status = False
        projects: dict[tuple[str, str], dict[str, Any]] = {
            (el["pnc_result"], el["pnc_state"]): el for el in pncs
        }
        tmp_table = make_tmp_table_name("project_names")
        response = self.send_sql_request(
            self.sql.get_cpes_by_project_names.format(
                tmp_table=tmp_table, cpe_states=PNC_STATES
            ),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [
                        ("project_name", "String"),
                    ],
                    "data": [{"project_name": el[0]} for el in projects.keys()],
                },
            ],
        )
        if not self.sql_status:
            return []
        if response:
            for p in (PncRecord(*el) for el in response):
                if (p.pkg_name, PNC_STATE_INACTIVE) in projects:
                    projects[(p.pkg_name, PNC_STATE_INACTIVE)].setdefault(
                        "cpes", []
                    ).append(p.asdict())
                if (p.pkg_name, PNC_STATE_ACTIVE) in projects:
                    projects[(p.pkg_name, PNC_STATE_ACTIVE)].setdefault(
                        "cpes", []
                    ).append(p.asdict())
        self.status = True
        return list(projects.values())

    def get(self):
        input_val = self.args.get("input")
        limit = self.args.get("limit")
        page = self.args.get("page")
        sort = self.args.get("sort")

        branch = self.args.get("branch")
        if branch:
            branch = (lut.repology_branch_map[branch],)
        else:
            branch = lut.repology_branches

        state = self.args.get("state")
        if state == "all":
            state = None

        # build where clause for PNC records gathering request
        where_conditions = ["WHERE 1"]

        if input_val:
            where_conditions.append(
                f"(arrayExists(x -> (x.1 ILIKE '%{input_val}%'), pkgs) OR result ILIKE '%{input_val}%')"
            )
        if state:
            where_conditions.append(f"state = '{state}'")

        where_clause = " AND ".join(where_conditions)

        # get PNC records from DB
        response = self.send_sql_request(
            self.sql.get_pnc_list.format(where_clause=where_clause, branch=branch)
        )
        if not self.sql_status:
            return self.error

        pnc_records = [
            PncListElement(el[0], el[1], [PncPackage(*pkg) for pkg in el[-1]]).asdict()
            for el in response
        ]

        if not pnc_records:
            return self.store_error(
                {"message": f"No data found in DB for {self.args}"}, http_code=404
            )

        if sort:
            pnc_records = rich_sort(pnc_records, sort)

        paginator = Paginator(pnc_records, limit)
        page_obj = paginator.get_page(page)

        page_obj = self._get_cpes(page_obj)
        if not self.status:
            return self.error

        res = {"request_args": self.args, "pncs": page_obj}

        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )
