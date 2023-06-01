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
# from altrepo_api.api.misc import lut

from .common import (
    CPE,
    CpeMatch,
    # Errata,
    PackageVersion,
    PackageVulnerability,
    VulnerabilityInfo,
    get_cve_info,
    get_packages_cpes,
    get_last_matched_packages_versions,
    get_packages_vulnerabilities,
    get_vulnerability_fix_errata,
)
from ..sql import sql

# from .common import VulnerabilityInfo


class VulnerablePackageByCve(APIWorker):
    """Retrieves vulnerable packages information by CVE id."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()
        self.branch: Union[str, None] = None
        self.cve_info: dict[str, VulnerabilityInfo] = {}
        self.cve_cpems: dict[str, list[CpeMatch]] = {}
        self.packages_cpes: dict[str, list[CPE]] = {}
        self.packages_versions: list[PackageVersion] = []
        self.packages_vulnerabilities: list[PackageVulnerability] = []

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

    def _find_vulnerable_packages(self, cve_ids: list[str]) -> None:
        # 1. get CVE information
        get_cve_info(self, tuple(cve_ids))
        if not self.status:
            return

        # 2. check if all CVE info found in database
        not_found = [cve_id for cve_id in cve_ids if cve_id not in self.cve_info]
        if not_found:
            _ = self.store_error(
                {"message": f"No CVE data info found in DB for {not_found}"}
            )
            self.status = False
            return

        # 3. Check if any packages has CPE matches
        get_packages_cpes(self)
        if not self.status:
            return

        # 4. find packages that mathces by CPE
        get_last_matched_packages_versions(self)
        if not self.status:
            return

        # 5. compare package and CVE versions
        get_packages_vulnerabilities(self)
        if not self.status:
            return

        # 6. check if there any buld tasks that fixes vulnerable packages
        get_vulnerability_fix_errata(self)
        if not self.status:
            return

    def get(self):
        self.branch = self.args["branch"]
        cve_ids = self.args["vuln_id"]

        self._find_vulnerable_packages(cve_ids)
        if not self.status:
            return self.error

        return {
            "request_args": self.args,
            "vuln_info": [vuln.asdict() for vuln in self.cve_info.values()],
            "packages": [p.asdict() for p in self.packages_vulnerabilities],
        }, 200

    def get_by_bdu(self):
        self.branch = self.args["branch"]
        bdu_id = self.args["vuln_id"]

        # get CVE id's from BDU
        response = self.send_sql_request(
            self.sql.get_vuln_info_by_ids.format(tmp_table=(bdu_id,))
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No data info found in DB for {bdu_id}"}
            )

        bdu = VulnerabilityInfo(*response[0][1:])

        cve_ids = []
        for idx, ref_type in enumerate(bdu.refs_type):
            if ref_type == "CVE":
                cve_ids.append(bdu.refs_link[idx])

        if not cve_ids:
            return self.store_error({"message": f"No related CVEs found in {bdu_id}"})

        self._find_vulnerable_packages(cve_ids)
        if not self.status:
            return self.error

        return {
            "request_args": self.args,
            "vuln_info": [bdu] + [vuln.asdict() for vuln in self.cve_info.values()],
            "packages": [p.asdict() for p in self.packages_vulnerabilities],
        }, 200
