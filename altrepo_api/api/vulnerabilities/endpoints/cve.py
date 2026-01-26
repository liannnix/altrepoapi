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

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut

from .common import (
    CPE,
    CpeMatch,
    Errata,
    PackageVersion,
    PackageVulnerability,
    VulnerabilityInfo,
    get_cve_info,
    get_packages_cpes,
    get_last_packages_versions,
    get_matched_packages_names,
    get_packages_vulnerabilities,
    get_vulnerability_fix_errata,
    get_errata_by_cve_ids,
    get_errata_by_pkg_names,
    deduplicate_erratas,
    CVE_ID_TYPE,
)
from ..sql import sql


class VulnerablePackageByCve(APIWorker):
    """Retrieves vulnerable packages information by CVE id."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()
        self.branch: str = self.args["branch"]
        self.cve_info: dict[str, VulnerabilityInfo] = {}
        self.cve_cpems: dict[str, list[CpeMatch]] = {}
        self.erratas: list[Errata] = []
        self.packages_cpes: dict[str, list[CPE]] = {}
        self.packages_versions: list[PackageVersion] = []
        self.packages_vulnerabilities: list[PackageVulnerability] = []
        self.result_message: list[str] = []

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def _find_vulnerable_packages(self, cve_ids: list[str]) -> None:
        # 1. get list of errata by CVE to Errata references matching
        get_errata_by_cve_ids(self, cve_ids, use_branch_inheritance=False)
        # XXX: do  not fail on 'self.status' here due to get errata for cls.branch only
        if not self.status:
            self.result_message.extend(
                [
                    f"No erratas found in DB for {cve_id} in branch {self.branch}"
                    for cve_id in cve_ids
                ]
            )
        if not self.sql_status:
            return

        package_names = {e.pkg_name for e in self.erratas}

        # 2. get CVE information
        get_cve_info(self, cve_ids, False)
        if not self.sql_status:
            return

        # 3. check if all CVE info found in database
        # add messages for not found CVE ids
        self.result_message.extend(
            [
                f"No data found in DB for {cve_id}"
                for cve_id in {
                    cve_id for cve_id in cve_ids if cve_id not in self.cve_info
                }
            ]
        )

        # add messages for CVEs without CPE matches
        self.result_message.extend(
            [
                f"No CPE matching data found in DB for {cve_id}"
                for cve_id in {
                    cve_id for cve_id in cve_ids if cve_id not in self.cve_cpems
                }
            ]
        )

        # if there is no data about CVE(s) found in DB at all use Errata as a source
        if not self.cve_info or not self.cve_cpems:
            self.result_message.append(
                f"Using errata history as a data source for {cve_ids}"
            )
        else:
            # 4. Check if any packages has CPE matches
            get_packages_cpes(self)
            if not self.sql_status:
                return
            if not self.status:
                self.result_message.extend(["Failed to get packages CPE from DB"])

            package_names.update(get_matched_packages_names(self))

        # 4.5 last try to get affected packages names from existing erratas
        if not package_names:
            if self.branch in lut.branch_inheritance:
                get_errata_by_cve_ids(self, cve_ids, use_branch_inheritance=True)
                if not self.status:
                    return
                package_names = {e.pkg_name for e in self.erratas}
            else:
                self.store_error(
                    {"message": f"No errata records found in DB for {cve_ids}"}
                )
                return

        # 5. get last packages versions
        get_last_packages_versions(self, package_names)
        if not self.status:
            return

        # 6. compare package and CVE versions
        get_packages_vulnerabilities(self)
        if not self.status:
            return

        # 7. get erratas by collected package names including tasks by branch inheritance
        get_errata_by_pkg_names(self, package_names)
        if not self.sql_status:
            return
        deduplicate_erratas(self)

        # 8. check if there any buld tasks that fixes vulnerable packages
        get_vulnerability_fix_errata(self, cve_ids)

    def get(self):
        cve_ids = self.args["vuln_id"]

        self._find_vulnerable_packages(cve_ids)
        if not self.status:
            return self.error

        return {
            "request_args": self.args,
            "vuln_info": [
                vuln.asdict(exclude_json=True)
                for vuln in sorted(self.cve_info.values(), key=lambda x: x.id)
            ],
            "packages": [
                p.asdict()
                for p in sorted(
                    self.packages_vulnerabilities,
                    key=lambda x: (x.vulnerable, x.name, x.fixed, x.vuln_id),
                )
            ],
            "result": self.result_message,
        }, 200

    def get_by_bdu(self):
        bdu_ids = self.args["vuln_id"]

        # get CVE id's from BDU
        response = self.send_sql_request(
            self.sql.get_vuln_info_by_ids.format(
                tmp_table=tuple(bdu_ids), json_field="'{}' AS vuln_json"
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No data info found in DB for {bdu_ids}"}
            )

        bdus = [VulnerabilityInfo(*el[1:]) for el in response]

        cve_ids = []
        for bdu in bdus:
            for idx, ref_type in enumerate(bdu.refs_type):
                if ref_type == CVE_ID_TYPE:
                    cve_ids.append(bdu.refs_link[idx])

        if not cve_ids:
            return self.store_error({"message": f"No related CVEs found in {bdu_ids}"})

        self._find_vulnerable_packages(cve_ids)
        if not self.status:
            return self.error

        return {
            "request_args": self.args,
            "result": self.result_message,
            "vuln_info": [
                bdu.asdict(exclude_json=True)
                for bdu in sorted(bdus, key=lambda x: x.id)
            ]
            + [
                vuln.asdict(exclude_json=True)
                for vuln in sorted(self.cve_info.values(), key=lambda x: x.id)
            ],
            "packages": [
                p.asdict()
                for p in sorted(
                    self.packages_vulnerabilities,
                    key=lambda x: (x.vulnerable, x.name, x.fixed, x.vuln_id),
                )
            ],
        }, 200
