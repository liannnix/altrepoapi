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
    REFERENCE_TYPE_VULN,
)
from ..sql import sql


class MaintainerOpenVulnerabilities(APIWorker):
    """Retrieves maintainer's packages open vulnerabilities information."""

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
        maintainer_nickname = self.args["maintainer_nickname"]
        by_acl = self.args["by_acl"]
        request_line = ""

        if by_acl == "by_nick":
            request_line = self.sql.get_maintainer_pkg_by_nick_acl.format(
                maintainer_nickname=maintainer_nickname, branch=self.branch
            )
        if by_acl == "by_nick_leader":
            request_line = self.sql.get_maintainer_pkg_by_nick_leader_acl.format(
                maintainer_nickname=maintainer_nickname, branch=self.branch
            )
        if by_acl == "by_nick_or_group":
            request_line = self.sql.get_maintainer_pkg_by_nick_or_group_acl.format(
                maintainer_nickname=maintainer_nickname, branch=self.branch
            )
        if by_acl == "by_nick_leader_and_group":
            request_line = (
                self.sql.get_maintainer_pkg_by_nick_leader_and_group_acl.format(
                    maintainer_nickname=maintainer_nickname, branch=self.branch
                )
            )
        if by_acl == "none":
            request_line = self.sql.get_maintainer_pkg.format(
                maintainer_nickname=maintainer_nickname, branch=self.branch
            )

        response = self.send_sql_request(request_line)
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        get_last_packages_versions(self, [el[0] for el in response])
        if not self.status:
            return self.error

        pkg_names = {p.name for p in self.packages_versions}

        # get erratas
        get_errata_by_pkg_names(self, pkg_names)
        if not self.sql_status:
            return self.error

        if not self.erratas:
            self.result_message.append(f"No errata found for {pkg_names}")

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
            {
                vuln_id
                for errata in self.erratas
                for vuln_id in errata.ref_ids(REFERENCE_TYPE_VULN)  # type: ignore
            }
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
                vuln.asdict(exclude_json=True)
                for vuln in sorted(vuln_info, key=lambda x: x.id)
            ],
            "packages": [p.asdict() for p in self.packages_vulnerabilities],
        }, 200
