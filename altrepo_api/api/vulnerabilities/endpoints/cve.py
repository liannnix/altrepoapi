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
        branch = self.args["branch"]  # XXX: is optional!
        vuln_id = self.args["vuln_id"]

        # 1. check if CVE info in DB
        response = self.send_sql_request(
            self.sql.get_vuln_info_by_id.format(vuln_id=vuln_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No data info found in DB for {vuln_id}"}
            )

        vuln_hash, vuln = response[0][0], VulnerabilityInfo(*response[0][1:])

        # 2. check if CPE matching is there
        response = self.send_sql_request(
            self.sql.get_cve_cpe_matching.format(vuln_hash=vuln_hash)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No CPE matches data info found in DB for {vuln_id}"}
            )

        cpems = [CpeMatch(*el) for el in response[0][0]]

        # 3. Check if any packages has CPE matches
        if branch is not None:
            # map key consistency is guaranteed by validation
            cpe_branches = (self.sql.CPE_BRANCH_MAP[branch],)
        else:
            cpe_branches = tuple({v for v in self.sql.CPE_BRANCH_MAP.values()})

        # 3.1 collect all packages CPEs
        response = self.send_sql_request(
            self.sql.get_packages_and_cpes.format(cpe_branches=cpe_branches)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No CPE matches data info found in DB for {vuln_id} in {cpe_branches}"
                }
            )

        packages_cpes: dict[str, list[CPE]] = {}
        for pkg_name, cpe in response:
            if pkg_name not in packages_cpes:
                packages_cpes[pkg_name] = []
            try:
                packages_cpes[pkg_name].append(CPE(cpe))
            except ValueError:
                self.logger.warning(f"Failed to parse CPE {cpe} for {pkg_name}")

        # 3.2 find packages that mathces by CPE
        matched_packages: list[tuple[str, CPE]] = []

        cve_cpe_triplets = {
            (cpem.cpe.vendor, cpem.cpe.product, cpem.cpe.target_sw) for cpem in cpems
        }

        for pkg, cpe in (
            (pkg, cpe) for pkg, cpes in packages_cpes.items() for cpe in cpes
        ):
            if (cpe.vendor, cpe.product, cpe.target_sw) in cve_cpe_triplets:
                matched_packages.append((pkg, cpe))

        # 4. check if last branch (all branches if `branch` not specified) packages are vulnerable
        branches = tuple(self.sql.CPE_BRANCH_MAP.keys())
        if branch is not None:
            branches = (branch,)

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
            return self.error
        if not response:
            return self.store_error({"message": "No packages data found in DB"})

        pkg_versions = [PackageVersion(*el) for el in response]

        # 4.1 compare package and CVE versions
        packages: list[PackageVulnerability] = []
        for pkg in pkg_versions:
            pkg_cpe_triplets = {
                (cpe.vendor, cpe.product, cpe.target_sw)
                for cpe in packages_cpes[pkg.name]
            }

            packages.append(
                PackageVulnerability(**pkg._asdict(), vuln_id=vuln_id).match_by_version(
                    (
                        cpem
                        for cpem in cpems
                        if (cpem.cpe.vendor, cpem.cpe.product, cpem.cpe.target_sw)
                        in pkg_cpe_triplets
                    )
                )
            )

            packages = sorted(
                packages, key=lambda x: (x.branch, x.vulnerable, x.name, x.version)
            )

        # 4.2 check if there any buld tasks that fixes vulnerable packages
        vulnearble_packages = [p for p in packages if p.vulnerable]

        if vulnearble_packages and (
            (branch is not None and branch in self.sql.ERRATA_LOOKUP_BRANCHES)
            or branch is None
        ):
            branches = (branch,)
            if branch is None:
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
                return self.error
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
                    return self.error
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
                            print("should delete", idx, errata.id, errata.task_id)
                            del pkg.fixed_in[idx]
                            continue
                        uniq_task_ids.add(errata.task_id)

                        # set `fixed` flag if task is `DONE` and update task state of errata
                        if task_states.get(errata.task_id) == "DONE":
                            errata.task_state = "DONE"
                            pkg.fixed = True

        return {
            "request_args": self.args,
            "vuln_info": vuln.asdict(),
            "packages": [p.asdict() for p in packages],
        }, 200
