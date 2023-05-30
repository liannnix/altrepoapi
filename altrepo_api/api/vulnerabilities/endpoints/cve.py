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

from typing import Iterable, Union

from altrepo_api.api.base import APIWorker
from altrepo_api.utils import make_tmp_table_name

from altrepo_api.api.misc import lut

from .common import (
    CPE,
    CpeMatch,
    Errata,
    PackageVersion,
    PackageVulnerability,
    VulnerabilityInfo,
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

    def _get_cve_info(self, cve_ids: Iterable[str]) -> None:
        self.status = False
        # 1. check if CVE info in DB
        tmp_table = make_tmp_table_name("vuiln_ids")

        response = self.send_sql_request(
            self.sql.get_vuln_info_by_ids.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("vuln_id", "String")],
                    "data": [{"vuln_id": cve_id} for cve_id in cve_ids],
                }
            ],
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error({"message": f"No data info found in DB for {cve_ids}"})
            return None

        cve_hashes: set[int] = set()
        for el in response:
            cve_hashes.add(el[0])
            self.cve_info[el[1]] = VulnerabilityInfo(*el[1:])

        # 2. check if CPE matching is there
        tmp_table = make_tmp_table_name("vuiln_hashes")

        response = self.send_sql_request(
            self.sql.get_cves_cpe_matching.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("vuln_hash", "UInt64")],
                    "data": [{"vuln_hash": h} for h in cve_hashes],
                }
            ],
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error(
                {"message": f"No CPE matches data info found in DB for {cve_ids}"}
            )
            return None

        self.cve_cpems: dict[str, list[CpeMatch]] = {
            el[0]: [CpeMatch(*x) for x in el[1]] for el in response
        }

        self.status = True

    def _get_packages_cpes(self) -> None:
        self.status = False

        cpe_branches = tuple({v for v in self.sql.CPE_BRANCH_MAP.values()})
        if self.branch is not None:
            cpe_branch = self.sql.CPE_BRANCH_MAP.get(self.branch, None)
            if cpe_branch is None:
                _ = self.store_error(
                    {"message": f"No CPE branch mapping found for branch {self.branch}"}
                )
                return None
            cpe_branches = (cpe_branch,)

        response = self.send_sql_request(
            self.sql.get_packages_and_cpes.format(cpe_branches=cpe_branches)
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error(
                {"message": f"No CPE matches data info found in DB for {cpe_branches}"}
            )
            return None

        for pkg_name, cpe in response:
            if pkg_name not in self.packages_cpes:
                self.packages_cpes[pkg_name] = []
            try:
                self.packages_cpes[pkg_name].append(CPE(cpe))
            except ValueError:
                self.logger.warning(f"Failed to parse CPE {cpe} for {pkg_name}")

        self.status = True

    def _get_last_matched_packages_versions(self) -> None:
        self.status = False
        matched_packages: list[tuple[str, CPE]] = []

        cve_cpe_triplets = {
            (cpem.cpe.vendor, cpem.cpe.product, cpem.cpe.target_sw)
            for cpems in self.cve_cpems.values()
            for cpem in cpems
        }

        for pkg, cpe in (
            (pkg, cpe) for pkg, cpes in self.packages_cpes.items() for cpe in cpes
        ):
            if (cpe.vendor, cpe.product, cpe.target_sw) in cve_cpe_triplets:
                matched_packages.append((pkg, cpe))

        # 4. check if last branch (all branches if `branch` not specified) packages are vulnerable
        branches = tuple(self.sql.CPE_BRANCH_MAP.keys())
        if self.branch is not None:
            branches = (self.branch,)

        tmp_table = make_tmp_table_name("pkg_names")

        response = self.send_sql_request(
            self.sql.get_packages_versions.format(
                branches=branches, tmp_table=tmp_table
            ),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("pkg_name", "String")],
                    "data": [{"pkg_name": p[0]} for p in matched_packages],
                }
            ],
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error({"message": "No packages data found in DB"})
            return None

        self.packages_versions = [PackageVersion(*el) for el in response]
        self.status = True

    def _get_packages_vulnerabilities(self) -> None:
        self.status = False

        for vuln_id, cpems in self.cve_cpems.items():
            cve_cpe_triplets = {
                (cpem.cpe.vendor, cpem.cpe.product, cpem.cpe.target_sw)
                for cpem in cpems
            }

            for pkg in self.packages_versions:
                pkg_cpe_triplets = {
                    (cpe.vendor, cpe.product, cpe.target_sw)
                    for cpe in self.packages_cpes[pkg.name]
                }

                if not cve_cpe_triplets.intersection(pkg_cpe_triplets):
                    continue

                self.packages_vulnerabilities.append(
                    PackageVulnerability(
                        **pkg._asdict(), vuln_id=vuln_id
                    ).match_by_version(
                        (
                            cpem
                            for cpem in cpems
                            if (cpem.cpe.vendor, cpem.cpe.product, cpem.cpe.target_sw)
                            in pkg_cpe_triplets
                        )
                    )
                )

        self.packages_vulnerabilities = sorted(
            self.packages_vulnerabilities,
            key=lambda x: (x.vuln_id, x.branch, x.vulnerable, x.name, x.version),
        )

        self.status = True

    def _get_vulnerability_fix_errata(self) -> None:
        self.status = False

        vulnearble_packages = [p for p in self.packages_vulnerabilities if p.vulnerable]

        if vulnearble_packages and (
            (self.branch is not None and self.branch in self.sql.ERRATA_LOOKUP_BRANCHES)
            or self.branch is None
        ):
            branches = (self.branch,)
            if self.branch is None:
                branches = tuple(self.sql.ERRATA_LOOKUP_BRANCHES)

            # get Errata where CVE is closed for vulnerable packages and not commited
            # to repository yet if any
            tmp_table = make_tmp_table_name("packages")

            response = self.send_sql_request(
                self.sql.get_errata_by_packages.format(
                    branches=branches, tmp_table=tmp_table
                ),
                external_tables=[
                    {
                        "name": tmp_table,
                        "structure": [("pkg_name", "String")],
                        "data": [{"pkg_name": p.name} for p in vulnearble_packages],
                    }
                ],
            )
            if not self.sql_status:
                return None
            if response:
                erratas = [Errata(*el[1]) for el in response]

                # get last state for tasks in erratas
                task_states: dict[int, str] = {}

                tmp_table = make_tmp_table_name("task_ids")

                response = self.send_sql_request(
                    self.sql.get_last_tasks_state.format(tmp_table=tmp_table),
                    external_tables=[
                        {
                            "name": tmp_table,
                            "structure": [("task_id", "UInt32")],
                            "data": [{"task_id": e.task_id} for e in erratas],
                        }
                    ],
                )
                if not self.sql_status:
                    return None
                if response:
                    task_states = {el[0]: el[1] for el in response}

                # check found erratas for vulnerability fixes
                for pkg in vulnearble_packages:
                    for errata in erratas:
                        if (pkg.name, pkg.branch) == (
                            errata.pkg_name,
                            errata.branch,
                        ) and pkg.vuln_id in errata.ref_ids(ref_type="vuln"):
                            # no need to check version due to branch, package name and vulnerability id is equal already
                            pkg.fixed_in.append(errata)

                    # if package in taskless branch and found any errata mark it as `fixed` and continue
                    if pkg.fixed_in and pkg.branch in lut.taskless_branches:
                        pkg.fixed = True
                        continue

                    uniq_task_ids: set[int] = set()
                    for idx, errata in enumerate(pkg.fixed_in[:]):
                        # delete duplicate errata by task id using that erratas are sorted by timestamp in descending order
                        if errata.task_id in uniq_task_ids:
                            del pkg.fixed_in[idx]
                            continue
                        uniq_task_ids.add(errata.task_id)

                        # set `fixed` flag if task is `DONE` and update task state of errata
                        if task_states.get(errata.task_id) == "DONE":
                            errata.task_state = "DONE"
                            pkg.fixed = True

        self.status = True

    def _get_vulnerable_packages(self, cve_ids: list[str]) -> None:
        # 1. get CVE information
        self._get_cve_info(tuple(cve_ids))
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
        self._get_packages_cpes()
        if not self.status:
            return

        # 4. find packages that mathces by CPE
        self._get_last_matched_packages_versions()
        if not self.status:
            return

        # 5. compare package and CVE versions
        self._get_packages_vulnerabilities()
        if not self.status:
            return

        # 6. check if there any buld tasks that fixes vulnerable packages
        self._get_vulnerability_fix_errata()
        if not self.status:
            return

    def get(self):
        self.branch = self.args["branch"]
        cve_ids = self.args["vuln_id"]

        self._get_vulnerable_packages(cve_ids)
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
        print(bdu)

        cve_ids = []
        for idx, ref_type in enumerate(bdu.refs_type):
            if ref_type == "CVE":
                cve_ids.append(bdu.refs_link[idx])

        if not cve_ids:
            return self.store_error({"message": f"No related CVEs found in {bdu_id}"})

        self._get_vulnerable_packages(cve_ids)
        if not self.status:
            return self.error

        return {
            "request_args": self.args,
            "vuln_info": [bdu] + [vuln.asdict() for vuln in self.cve_info.values()],
            "packages": [p.asdict() for p in self.packages_vulnerabilities],
        }, 200
