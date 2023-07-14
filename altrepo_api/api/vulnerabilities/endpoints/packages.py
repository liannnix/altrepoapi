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

from typing import Union

from altrepo_api.api.base import APIWorker

from .common import (
    CPE,
    CpeMatch,
    Errata,
    PackageVersion,
    PackageVulnerability,
    VulnerabilityInfo,
    get_cve_info_by_ids,
    get_cve_matching_by_cpes,
    get_errata_by_pkg_names,
    get_last_packages_versions,
    get_packages_cpes,
    get_packages_vulnerabilities,
    get_vulnerability_fix_errata,
)
from ..sql import sql


class PackageOpenVulnerabilities(APIWorker):
    """Retrieves package's open vulnerabilities information."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()
        self.branch: Union[str, None] = None
        self.cve_info: dict[str, VulnerabilityInfo] = {}
        self.cve_cpems: dict[str, list[CpeMatch]] = {}
        self.erratas: list[Errata] = []
        self.packages_cpes: dict[str, list[CPE]] = {}
        self.packages_versions: list[PackageVersion] = []
        self.packages_vulnerabilities: list[PackageVulnerability] = []
        self.result_message: list[str] = []

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        branch = self.args["branch"]
        if branch is not None and branch not in self.sql.CPE_BRANCH_MAP:
            self.validation_results.append(
                f"No CPE matches is specified for branch {branch}. "
                f"Use one of: {', '.join(self.sql.CPE_BRANCH_MAP.keys())}"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args["branch"]
        pkg_names = (self.args["name"],)

        # get erratas
        get_errata_by_pkg_names(self, pkg_names)
        if not self.sql_status:
            return self.error

        if not self.erratas:
            self.result_message.append(f"No errata found for {pkg_names}")

        # get last package versions
        get_last_packages_versions(self, pkg_names)
        if not self.status:
            return self.error

        # get packages CPEs if any
        get_packages_cpes(self, {p.name for p in self.packages_versions})
        if not self.sql_status:
            return self.error

        if self.packages_cpes:
            get_cve_matching_by_cpes(self)
            if not self.sql_status:
                return self.error
        else:
            self.result_message.append(f"No CPE matches found for {pkg_names}")

        cve_ids = set(self.cve_cpems.keys())
        cve_ids.update(
            {vuln_id for errata in self.erratas for vuln_id in errata.ref_ids("vuln")}
        )
        get_cve_info_by_ids(self, cve_ids, False)
        if not self.sql_status:
            return self.error

        self.result_message.extend(
            [
                f"No data found in DB for {cve_id}"
                for cve_id in {
                    cve_id for cve_id in cve_ids if cve_id not in self.cve_info
                }
            ]
        )

        get_packages_vulnerabilities(self)
        # filter only vulnerable packages found by CPE matching version compare
        self.packages_vulnerabilities = [
            pv for pv in self.packages_vulnerabilities if pv.vulnerable
        ]

        # update packagex vulnerabilities with erratas data
        get_vulnerability_fix_errata(self, cve_ids)
        # filter only vulnerable packages found by CPE matching version compare
        self.packages_vulnerabilities = [
            pv for pv in self.packages_vulnerabilities if pv.vulnerable
        ]

        # collect vulnerabilities info
        vuln_info: list[VulnerabilityInfo] = []
        for vuln_id in {pv.vuln_id for pv in self.packages_vulnerabilities}:
            vi = self.cve_info.get(vuln_id)
            if vi is not None:
                vuln_info.append(vi)

        return {
            "request_args": self.args,
            "result": self.result_message,
            "vuln_info": [
                vuln.asdict() for vuln in sorted(vuln_info, key=lambda x: x.id)
            ],
            "packages": [p.asdict() for p in self.packages_vulnerabilities],
        }, 200
