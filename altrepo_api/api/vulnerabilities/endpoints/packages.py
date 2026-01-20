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

from dataclasses import dataclass, asdict
from typing import Any, Iterable, Union

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.utils import make_tmp_table_name
from .fixes import PackageMeta

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
    BDU_ID_PREFIX,
)
from ..sql import sql


@dataclass
class PackageScheme(PackageMeta):
    last_version: Union[PackageMeta, None] = None

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


class PackageOpenVulnerabilities(APIWorker):
    """Retrieves package's open vulnerabilities information."""

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
                f"No data found in DB for mentioned {cve_id} vulnerability"
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

        # update packages vulnerabilities with erratas data
        get_vulnerability_fix_errata(self, cve_ids)
        # filter only vulnerable packages using found errata fixes
        self.packages_vulnerabilities = [
            pv for pv in self.packages_vulnerabilities if pv.vulnerable
        ]

        # collect vulnerabilities info
        vuln_info: list[VulnerabilityInfo] = []
        for vuln_id in {pv.vuln_id for pv in self.packages_vulnerabilities}:
            vi = self.cve_info.get(vuln_id)
            if vi is not None:
                vuln_info.append(vi)

        if not self.packages_vulnerabilities:
            self.result_message = ["No vulnerable packages found"] + self.result_message

        return {
            "request_args": self.args,
            "result": self.result_message,
            "vuln_info": [
                vuln.asdict(exclude_json=True)
                for vuln in sorted(vuln_info, key=lambda x: x.id)
            ],
            "packages": [p.asdict() for p in self.packages_vulnerabilities],
        }, 200


class PackagesByOpenVuln(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()
        self.status: bool = False
        self.packages: list[PackageScheme] = []
        self.packages_versions: dict[tuple[str, str], PackageVersion] = dict()

    def _get_packages_by_vuln(self):
        """
        Get packages which has vulnerability matched as open
        """
        self.status = False

        tmp_table_name = make_tmp_table_name("vuln")
        response = self.send_sql_request(
            self.sql.get_packages_with_open_vuln.format(tmp_table=tmp_table_name),
            external_tables=[
                {
                    "name": tmp_table_name,
                    "structure": [
                        ("vuln_id", "String"),
                    ],
                    "data": [{"vuln_id": el} for el in self.vuln_id],
                }
            ],
        )
        if not response:
            _ = self.store_error(
                {
                    "message": "No packages found with open vulnerability",
                    "args": self.args,
                }
            )
            return
        if not self.sql_status:
            return

        self.packages = [PackageScheme(*package) for package in response]

        self.status = True

    def _get_bdu_related_cve(self):
        """
        Get BDU related CVE ids
        """
        self.status = False

        response = self.send_sql_request(
            self.sql.get_bdu_related_cves.format(bdu_id=self.vuln_id[0])
        )

        if not self.sql_status:
            return
        if response:
            self.vuln_id = response[0][0]

        self.status = True

    def _get_last_packages_versions(self, pkg_names: Iterable[str]) -> None:
        """
        Get last package versions for active branches.
        """
        self.status = False
        tmp_table = make_tmp_table_name("pkg_names")

        response = self.send_sql_request(
            self.sql.get_packages_versions_for_show_branches.format(
                tmp_table=tmp_table
            ),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("pkg_name", "String")],
                    "data": [{"pkg_name": p} for p in pkg_names],
                }
            ],
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error({"message": "No packages data found in DB"})
            return None

        self.packages_versions = {
            (el[1], el[-1]): PackageVersion(*el) for el in response
        }
        self.status = True

    def get(self):
        self.vuln_id = [
            self.args["vuln_id"],
        ]

        if self.vuln_id[0].startswith(BDU_ID_PREFIX):
            self._get_bdu_related_cve()
            if not self.status:
                return self.error

        self._get_packages_by_vuln()
        if not self.status:
            return self.error

        packages = {
            (package.name, package.branch): package
            for package in self.packages
            if package.branch in lut.known_branches
        }

        self._get_last_packages_versions(
            set([package.name for package in packages.values()])
        )

        for key in packages:
            last_version = self.packages_versions.get(key)
            if last_version:
                packages[key].last_version = PackageMeta(
                    pkghash=last_version.hash,
                    name=last_version.name,
                    branch=last_version.branch,
                    version=last_version.version,
                    release=last_version.release,
                )

        packages = [
            package.asdict()
            for package in packages.values()
            if package.last_version is not None
        ]

        res = {"request_args": self.args, "length": len(packages), "packages": packages}

        return res, 200
