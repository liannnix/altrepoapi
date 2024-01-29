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

from flask import request
from typing import Any

from altrepodb_libs import (
    PackageCVEMatcher,
    PackageCveMatch,
    PackageCpePair,
    DatabaseConfig,
    convert_log_level,
)

from altrepo_api.settings import namespace as settings

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.utils import make_tmp_table_name

from .processing import ErrataBuilder, ErrataBuilderError, ErrataHandler, ErrataHandlerError
from .processing.base import (
    CPE,
    CpeRaw,
    CpeRecord,
    compare_pnc_records,
    cpe_record2pnc_record,
    uniq_pcm_records,
)
from .tools.base import ChangeSource, PncRecord, UserInfo
from .tools.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_DISCARD,
    CHANGE_ACTION_UPDATE,
    # CHANGE_SOURCE_KEY,
    # CHANGE_SOURCE_MANUAL,
    DRY_RUN_KEY,
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
from .tools.utils import validate_action, validate_branch_with_tatsks
from ..sql import sql

MATCHER_LOG_LEVEL = convert_log_level(settings.LOG_LEVEL)
RETUNRN_VULNERABLE_ONLY_PCMS = False


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

        response = self.send_sql_request(
            self.sql.get_cpes.format(
                cpe_branches=tuple(set(lut.cpe_reverse_branch_map.keys())),
                pkg_name_conversion_clause="",
                cpe_states=(PNC_STATE_CANDIDATE,),
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"Error": "No CPE candidates found in DB"})

        for el in response:
            try:
                cpe_raw = CpeRaw(*el)

                branch = lut.cpe_reverse_branch_map[cpe_raw.repology_branch][0]
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

        res = {
            "length": len(cpes),
            "cpes": [
                {"cpe": k[0], "repology_name": k[1], **v} for k, v in cpes.items()
            ],
        }

        return res, 200


class ManageCpe(APIWorker):
    """CPE records management handler."""

    def __init__(self, connection, payload, **kwargs):
        self.payload: dict[str, Any] = payload
        self.dry_run = kwargs.get(DRY_RUN_KEY, False)
        # FIXME: change_source set to 'AUTO' to be used during Erratas updates
        # self.change_source = ChangeSource.from_string(
        #     kwargs.get(CHANGE_SOURCE_KEY, CHANGE_SOURCE_MANUAL)
        # )
        self.change_source = ChangeSource.AUTO
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.trx = Transaction(source=ChangeSource.MANUAL)
        # values set in self.check_params_xxx() call
        self.user_info: UserInfo
        self.action: str
        self.cpes: list[CpeRecord] = []
        super().__init__()

    def _valiadte_and_parse(self):
        """Validate and parse `self.payload' JSON contents."""

        self.user_info = UserInfo(
            ip=request.remote_addr or "",
            name=self.payload.get("user", ""),
            reason=self.payload.get("reason", ""),
        )

        self.action = self.payload.get("action", "")

        if not self.user_info.name:
            self.validation_results.append("User name should be specified")

        if not self.user_info.reason and not self.dry_run:
            self.validation_results.append("CPE change reason should be specified")

        if not validate_action(self.action):
            self.validation_results.append(
                f"CPE change action '{self.action}' not supported"
            )

        cpes: list[dict[str, str]] = self.payload.get("cpes", [])
        if not cpes:
            self.validation_results.append("No CPE records objects found")
            return
        else:
            for el in cpes:
                try:
                    cpe = CpeRecord(
                        cpe=CPE(el["cpe"]),
                        state=el["state"],
                        project_name=el["project_name"],
                    )

                    if not cpe.project_name or not cpe.state:
                        raise ValueError("Required fields values are empty")

                    if cpe.state not in PNC_STATES:
                        raise ValueError(f"Invalid CPE record state: {cpe.state}")

                    self.cpes.append(cpe)
                except Exception as e:
                    self.validation_results.append(
                        f"Failed to parse CPE record objects {el}: {e}"
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

    def _get_pkgss_cve_matches_by_hashes(
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

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        branch = self.args.get("branch", None)
        if branch is not None and not validate_branch_with_tatsks(branch):
            self.validation_results.append(f"Invalid branch: {self.args['branch']}")
            return False

        return True

    def check_params_post(self) -> bool:
        self._valiadte_and_parse()

        if not self.action == CHANGE_ACTION_CREATE:
            self.validation_results.append("Change action validation error")

        for cpe in self.cpes:
            if cpe.state in (PNC_STATE_INACTIVE, PNC_STATE_CANDIDATE):
                self.validation_results.append(
                    f"Invalid CPE match record state: {cpe.asdict()}"
                )

        if self.validation_results != []:
            return False
        return True

    def check_params_put(self) -> bool:
        self._valiadte_and_parse()

        if not self.action == CHANGE_ACTION_UPDATE:
            self.validation_results.append("Change action validation error")

        for cpe in self.cpes:
            if cpe.state != PNC_STATE_ACTIVE:
                self.validation_results.append(
                    f"Invalid CPE match record state: {cpe.asdict()}"
                )

        if self.validation_results != []:
            return False
        return True

    def check_params_delete(self) -> bool:
        self._valiadte_and_parse()

        if not self.action == CHANGE_ACTION_DISCARD:
            self.validation_results.append("Change action validation error")

        for cpe in self.cpes:
            if cpe.state != PNC_STATE_INACTIVE:
                self.validation_results.append(
                    f"Invalid CPE match record state: {cpe.asdict()}"
                )

        if self.validation_results != []:
            return False
        return True

    def get(self):
        """Get CPE records, active and candidate, by package name
        and branch (optional)."""

        cpes: dict[tuple[str, str], Any] = {}

        pkg_name = self.args["name"]
        branch = self.args.get("branch")
        if branch is None:
            branch = ""
            cpe_branches = tuple(set(lut.cpe_reverse_branch_map.keys()))
        else:
            cpe_branches = (lut.cpe_branch_map[branch],)

        # get last CPE match states for specific package name
        response = self.send_sql_request(
            self.sql.get_cpes.format(
                cpe_branches=cpe_branches,
                pkg_name_conversion_clause=f"AND alt_name = '{pkg_name}'",
                cpe_states=(PNC_STATE_ACTIVE, PNC_STATE_CANDIDATE, PNC_STATE_INACTIVE),
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"Error": f"No CPE records found in DB for package '{pkg_name}'"}
            )

        for el in response:
            try:
                cpe_raw = CpeRaw(*el)

                _branch = lut.cpe_reverse_branch_map[cpe_raw.repology_branch][0]
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
            "name": pkg_name,
            "branch": branch,
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
        response = self.send_sql_request(
            self.sql.get_cpes_by_project_names.format(
                project_names=tuple({cpe.project_name for cpe in self.cpes}),
                cpe_states=(PNC_STATE_ACTIVE, PNC_STATE_CANDIDATE, PNC_STATE_INACTIVE),
            )
        )
        if not self.sql_status:
            return self.error
        if response:
            for p in (PncRecord(*el) for el in response):
                db_cpes.setdefault(p.pkg_name, []).append(p)

        # check if any records already exists in DB
        if db_cpes:
            for cpe in self.cpes:
                pncr = cpe_record2pnc_record(cpe)
                for p in db_cpes.get(cpe.project_name, []):
                    if compare_pnc_records(pncr, p, include_state=False):
                        return self.store_error(
                            {
                                "message": f"CPE record already exists in DB: {p}.",
                            },
                            http_code=409,
                        )

        # check if there is any packages that affected by added CPE records in branches
        related_packages = get_related_packages_by_project_name(
            self, list({c.project_name for c in self.cpes})
        )
        if not self.status:
            return self.error

        # create and store new CPE match records
        for cpe in self.cpes:
            self.trx.register_pnc_create(
                pnc=cpe_record2pnc_record(cpe), pnc_type=PncType.CPE
            )

        self.trx.commit(self.user_info)

        related_cve_ids: list[str] = []
        packages_cve_matches: list[dict[str, Any]] = []
        eb = ErrataBuilder(
            connection=self.conn, branches=lut.errata_manage_branches_with_tasks
        )
        eh = ErrataHandler(self.conn, self.user_info, self.trx._id, self.dry_run)

        if related_packages:
            # update PackagesCveMatch table
            pkg_cpe_pairs = [
                PackageCpePair(name=cpe.project_name, cpe=str(cpe.cpe))
                for cpe in self.cpes
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
            matcher.match_cpe_add(pkg_cpe_pairs)

            pcms = matcher.packages_cve_matches
            related_cve_ids = sorted({m.vuln_id for m in pcms})

            if not self.dry_run:
                matcher.store()

            matcher.free(full=True)
            del matcher

            # collect packages info from latest branch states
            packages_cve_matches = self._collect_packages_cve_match_info(pcms)

            # FIXME: update or create erratas
            raise NotImplementedError("Errata processing not implemented")

        # store PNC and PNC change records
        if not self.dry_run:
            store_pnc_records(self, self.trx.pnc_records)
            if not self.sql_status:
                return self.error
            store_pnc_change_records(self, self.trx.pnc_change_records)
            if not self.sql_status:
                return self.error

        return {
            "user": self.user_info.name,
            "action": self.action,
            "reason": self.user_info.reason,
            "message": "OK",
            "cpes": [c.asdict() for c in self.cpes],
            "related_packages": related_packages,
            "related_cve_ids": related_cve_ids,
            "cpe_records": [r.asdict() for r in self.trx.pnc_records],
            "cpe_change_records": [r.asdict() for r in self.trx.pnc_change_records],
            "errata_records": eh.errata_records,
            "errata_change_records": eh.errata_change_records,
            "packages_cve_matches": packages_cve_matches,
        }, 200

    def put(self):
        """Handles CPE record update.
        Returns:
            - 200 (OK) if CPE record was updated or no changes found to be made
            - 400 (Bad request) on paload validation errors
            - 404 (Not found) if CPE record does not exists
        """
        # get CPE match records by `project_name`
        db_cpes: dict[str, list[PncRecord]] = {}
        response = self.send_sql_request(
            self.sql.get_cpes_by_project_names.format(
                project_names=tuple({cpe.project_name for cpe in self.cpes}),
                cpe_states=(PNC_STATE_ACTIVE, PNC_STATE_CANDIDATE, PNC_STATE_INACTIVE),
            )
        )
        if not self.sql_status:
            return self.error
        if response:
            for p in (PncRecord(*el) for el in response):
                db_cpes.setdefault(p.pkg_name, []).append(p)

        # check if any records are doesn't exists in DB
        if not db_cpes:
            return self.store_error(
                {
                    "message": "no corresponding CPE match records found in DB to be updated"
                },
                http_code=404,
            )
        else:
            found_missing = False

            for cpe in self.cpes:
                pncr = cpe_record2pnc_record(cpe)
                found_missing = True

                for p in db_cpes.get(cpe.project_name, []):
                    if compare_pnc_records(pncr, p, include_state=False):
                        found_missing = False
                        break

                if found_missing:
                    return self.store_error(
                        {
                            "message": f"CPE match record not found in DB to be updated: {cpe}.",
                        },
                        http_code=404,
                    )

        # check if any updates are ever exists
        # copy CPE objects list here
        cpes_copy = self.cpes[:]

        # remove CPE records that already exists in DB
        for cpe in self.cpes:
            pncr = cpe_record2pnc_record(cpe)
            for p in db_cpes.get(cpe.project_name, []):
                if compare_pnc_records(pncr, p, include_state=True):
                    try:
                        cpes_copy.remove(cpe)
                        break
                    except ValueError:
                        pass

            if not cpes_copy:
                return {
                    "user": self.user_info.name,
                    "action": self.action,
                    "reason": self.user_info.reason,
                    "message": "No changes found to be stored to DB",
                    "cpes": [c.asdict() for c in self.cpes],
                    "related_packages": [],
                    "related_cve_ids": [],
                    "cpe_records": [],
                    "cpe_change_records": [],
                    "packages_cve_matches": [],
                }, 200

        # check if there is any packages that affected by added CPE records in branches
        related_packages = get_related_packages_by_project_name(
            self, list({c.project_name for c in cpes_copy})
        )
        if not self.status:
            return self.error

        # create and store new CPE match records
        for cpe in cpes_copy:
            self.trx.register_pnc_create(
                pnc=cpe_record2pnc_record(cpe), pnc_type=PncType.CPE
            )

        self.trx.commit(self.user_info)

        related_cve_ids: list[str] = []
        packages_cve_matches: list[dict[str, Any]] = []
        eb = ErrataBuilder(
            connection=self.conn, branches=lut.errata_manage_branches_with_tasks
        )
        eh = ErrataHandler(self.conn, self.user_info, self.trx._id, self.dry_run)

        if related_packages:
            # update PackagesCveMatch table
            pkg_cpe_pairs = [
                PackageCpePair(name=cpe.project_name, cpe=str(cpe.cpe))
                for cpe in cpes_copy
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
            matcher.match_cpe_add(pkg_cpe_pairs)

            pcms = matcher.packages_cve_matches
            # XXX: if all packages' CVE matches already loaded use hashes from matcher
            if not pcms and matcher.packages_cve_match_hashes:
                self.logger.info(
                    "Got no new packages' CVE matches, use existing hashes"
                )
                pcms = self._get_pkgss_cve_matches_by_hashes(
                    matcher.packages_cve_match_hashes
                )
                if not self.status:
                    return self.error

            related_cve_ids = sorted({m.vuln_id for m in pcms})

            if not self.dry_run:
                matcher.store()

            matcher.free(full=True)
            del matcher

            # collect packages info from latest branch states
            packages_cve_matches = self._collect_packages_cve_match_info(pcms)

            # XXX: update or create erratas
            try:
                erratas = eb.build_erratas_on_cpe_add(pcms)
                eh.commit(*erratas)
            except ErrataBuilderError:
                return eb.error
            except ErrataHandlerError:
                return eh.error

        # store PNC and PNC change records
        if not self.dry_run:
            store_pnc_records(self, self.trx.pnc_records)
            if not self.sql_status:
                return self.error
            store_pnc_change_records(self, self.trx.pnc_change_records)
            if not self.sql_status:
                return self.error

        return {
            "user": self.user_info.name,
            "action": self.action,
            "reason": self.user_info.reason,
            "message": "OK",
            "cpes": [c.asdict() for c in self.cpes],
            "related_packages": related_packages,
            "related_cve_ids": related_cve_ids,
            "cpe_records": [r.asdict() for r in self.trx.pnc_records],
            "cpe_change_records": [r.asdict() for r in self.trx.pnc_change_records],
            "errata_records": eh.errata_records,
            "errata_change_records": eh.errata_change_records,
            "packages_cve_matches": packages_cve_matches,
        }, 200

    def delete(self):
        """Handles CPE record discard.
        Returns:
            - 200 (OK) if CPE record discarded successfully
            - 400 (Bad request) on paload validation errors
            - 404 (Not found) if CPE record is discarded already or does not exists
        """
        # get CPE match records by `project_name`
        db_cpes: dict[str, list[PncRecord]] = {}
        response = self.send_sql_request(
            self.sql.get_cpes_by_project_names.format(
                project_names=tuple({cpe.project_name for cpe in self.cpes}),
                cpe_states=(PNC_STATE_ACTIVE, PNC_STATE_CANDIDATE, PNC_STATE_INACTIVE),
            )
        )
        if not self.sql_status:
            return self.error
        if response:
            for p in (PncRecord(*el) for el in response):
                db_cpes.setdefault(p.pkg_name, []).append(p)

        # check if any records are doesn't exists in DB
        if not db_cpes:
            return self.store_error(
                {
                    "message": "no corresponding CPE match records found in DB to be updated"
                },
                http_code=404,
            )
        else:
            found_missing = False

            for cpe in self.cpes:
                pncr = cpe_record2pnc_record(cpe)
                found_missing = True

                for p in db_cpes.get(cpe.project_name, []):
                    if compare_pnc_records(pncr, p, include_state=False):
                        found_missing = False
                        break

                if found_missing:
                    return self.store_error(
                        {
                            "message": f"CPE match record not found in DB to be updated: {cpe}.",
                        },
                        http_code=404,
                    )

        # check if any updates are ever exists
        # copy CPE objects list here
        cpes_copy = self.cpes[:]

        # remove CPE records that already exists in DB
        for cpe in self.cpes:
            pncr = cpe_record2pnc_record(cpe)
            for p in db_cpes.get(cpe.project_name, []):
                if compare_pnc_records(pncr, p, include_state=True):
                    try:
                        cpes_copy.remove(cpe)
                        break
                    except ValueError:
                        pass

            if not cpes_copy:
                return {
                    "user": self.user_info.name,
                    "action": self.action,
                    "reason": self.user_info.reason,
                    "message": "No changes found to be stored to DB",
                    "cpes": [c.asdict() for c in self.cpes],
                    "related_packages": [],
                    "related_cve_ids": [],
                    "cpe_records": [],
                    "cpe_change_records": [],
                    "packages_cve_matches": [],
                }, 200

        # check if there is any packages that affected by added CPE records in branches
        related_packages = get_related_packages_by_project_name(
            self, list({c.project_name for c in cpes_copy})
        )
        if not self.status:
            return self.error

        # create and store new CPE match records
        for cpe in cpes_copy:
            self.trx.register_pnc_discard(
                pnc=cpe_record2pnc_record(cpe), pnc_type=PncType.CPE
            )

        self.trx.commit(self.user_info)

        related_cve_ids: list[str] = []
        packages_cve_matches: list[dict[str, Any]] = []
        eb = ErrataBuilder(
            connection=self.conn, branches=lut.errata_manage_branches_with_tasks
        )
        eh = ErrataHandler(self.conn, self.user_info, self.trx._id, self.dry_run)

        if related_packages:
            # update PackagesCveMatch table
            pkg_cpe_pairs = [
                PackageCpePair(name=cpe.project_name, cpe=str(cpe.cpe))
                for cpe in cpes_copy
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
            matcher.match_cpe_delete(pkg_cpe_pairs)

            pcms = matcher.packages_cve_matches
            related_cve_ids = sorted({m.vuln_id for m in pcms})

            if not self.dry_run:
                matcher.store()

            matcher.free(full=True)
            del matcher

            # collect packages info from latest branch states
            packages_cve_matches = self._collect_packages_cve_match_info(pcms)

            # FIXME: update or create erratas
            raise NotImplementedError("Errata processing not implemented")

        # store PNC and PNC change records
        if not self.dry_run:
            store_pnc_records(self, self.trx.pnc_records)
            if not self.sql_status:
                return self.error
            store_pnc_change_records(self, self.trx.pnc_change_records)
            if not self.sql_status:
                return self.error

        return {
            "user": self.user_info.name,
            "action": self.action,
            "reason": self.user_info.reason,
            "message": "OK",
            "cpes": [c.asdict() for c in self.cpes],
            "related_packages": related_packages,
            "related_cve_ids": related_cve_ids,
            "cpe_records": [r.asdict() for r in self.trx.pnc_records],
            "cpe_change_records": [r.asdict() for r in self.trx.pnc_change_records],
            "errata_records": eh.errata_records,
            "errata_change_records": eh.errata_change_records,
            "packages_cve_matches": packages_cve_matches,
        }, 200

    def _rollback_on_failuer(self, eb: ErrataBuilder, eh: ErrataHandler):
        pass
