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

from altrepo_api.api.base import APIWorker

from .common import (
    CPE,
    CpeMatch,
    Errata,
    PackageVersion,
    PackageVulnerability,
    PackageVulnerabiltyInfo,
    Vulnerability,
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


class BranchOpenVulnerabilities(APIWorker):
    """Retrieves branch packages open vulnerabilities information."""

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

    def get(self):
        # get branch source packages
        response = self.send_sql_request(
            self.sql.get_branch_src_packages.format(branch=self.branch)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No source packages data found in DB for {self.branch}"}
            )

        get_last_packages_versions(self, [el[0] for el in response])
        if not self.status:
            return self.error

        pkg_names = {p.name for p in self.packages_versions}

        # get erratas
        get_errata_by_pkg_names(self, pkg_names)
        if not self.status:
            return self.error

        # get packages CPEs if any
        get_packages_cpes(self, pkg_names)
        if not self.status:
            return self.error

        get_cve_matching_by_cpes(self)
        if not self.sql_status:
            return self.error

        cve_ids = set(self.cve_cpems.keys())
        cve_ids.update(
            {vuln_id for errata in self.erratas for vuln_id in errata.ref_ids("vuln")}
        )
        # exclude vulnerabilities JSON field here
        get_cve_info_by_ids(self, cve_ids, True)
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

        # build human readable compact response
        result: dict[str, PackageVulnerabiltyInfo] = {}

        for pv in self.packages_vulnerabilities:
            # build new container
            if pv.name not in result:
                result[pv.name] = PackageVulnerabiltyInfo(
                    pv.name, pv.version, pv.release, pv.branch
                )
            # update with data
            if pv.cpe_matches or pv.vuln_id not in {
                v.id for v in result[pv.name].vulnerabilities
            }:
                result[pv.name].vulnerabilities.append(
                    Vulnerability(id=pv.vuln_id, cpe_matches=pv.cpe_matches)
                )
            result[pv.name].fixed_in.update(pv.fixed_in)

        return {
            "request_args": self.args,
            "result": self.result_message,
            "vuln_info": [
                vuln.asdict() for vuln in sorted(vuln_info, key=lambda x: x.id)
            ],
            # "packages": [p.asdict() for p in self.packages_vulnerabilities],
            "packages": [p.asdict() for p in result.values()],
        }, 200
