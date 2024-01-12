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

from dataclasses import dataclass
from typing import Iterable, NamedTuple, Union

from altrepodb_libs import (
    PackageCveMatch,
    VersionCompareResult,
    version_compare,
    version_less_or_equal,
)

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.api.vulnerabilities.endpoints.common import CpeMatchVersions

# from altrepo_api.libs.librpm_functions import compare_versions, VersionCompareResult
from altrepo_api.utils import make_tmp_table_name

from .tools.base import Errata, ErrataID, Reference


class ErrataBuilderError(Exception):
    pass


@dataclass(frozen=True)
class SQL:
    get_erratas_by_pkgs_names = """
SELECT EI.*, DE.discarded_id as discarded_id
FROM (
    SELECT *
    FROM ErrataHistory
    WHERE errata_id IN (
        SELECT eid
        FROM (
            SELECT
                errata_id_noversion,
                argMax(errata_id, errata_id_version) AS eid
            FROM ErrataHistory
            WHERE eh_type = 'task' AND task_state = 'DONE'
                AND pkgset_name IN {branches}
                AND pkg_name IN {tmp_table}
            GROUP BY errata_id_noversion
        )
    )
) AS EI
LEFT JOIN (
    SELECT errata_id AS discarded_id
    FROM last_discarded_erratas
) AS DE ON errata_id = DE.discarded_id
"""

    get_erratas_by_cve_ids = """
WITH
(
    SELECT groupUniqArray(cve_id) FROM {tmp_table}
) AS cve_ids
SELECT EI.*, DE.discarded_id as discarded_id
FROM (
    SELECT *
    FROM ErrataHistory
    WHERE errata_id IN (
        SELECT eid
        FROM (
            SELECT
                errata_id_noversion,
                argMax(errata_id, errata_id_version) AS eid
            FROM ErrataHistory
            WHERE eh_type = 'task' AND task_state = 'DONE'
                AND pkgset_name IN {branches}
                AND hasAny(eh_references.link, cve_ids)
            GROUP BY errata_id_noversion
        )
    )
) AS EI
LEFT JOIN (
    SELECT errata_id AS discarded_id
    FROM last_discarded_erratas
) AS DE ON errata_id = DE.discarded_id
"""

    get_packages_versions = """
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release
FROM Packages
WHERE pkg_hash IN {tmp_table}
    AND pkg_sourcepackage = 1
"""

    get_done_tasks_by_packages = """
WITH
tasks_history AS (
    SELECT DISTINCT
        task_id,
        task_changed,
        pkgset_name,
        pkg_hash,
        pkg_name,
        pkg_version,
        pkg_release
    FROM BranchPackageHistory
    WHERE pkgset_name in {branches}
        AND pkg_name IN {tmp_table}
        AND pkg_sourcepackage = 1
        AND tplan_action = 'add'
    ORDER BY task_changed DESC
)
SELECT DISTINCT
    task_id,
    subtask_id,
    pkgset_name,
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release
FROM tasks_history
LEFT JOIN (
    SELECT
        task_id,
        subtask_id,
        titer_srcrpm_hash AS pkg_hash
    FROM TaskIterations
    WHERE (task_id, task_changed, pkg_hash) IN (
        SELECT task_id, task_changed, pkg_hash FROM tasks_history
    )
) AS subtasks USING (task_id, pkg_hash)
"""

    get_cve_versions_matches = """
SELECT
    vuln_id,
    vuln_hash,
    cpe_hash,
    cpm_version_hash,
    cpm_version_start,
    cpm_version_end,
    cpm_version_start_excluded,
    cpm_version_end_excluded
FROM CpeMatch
WHERE (vuln_hash, cpe_hash, cpm_version_hash) IN {tmp_table}
"""


class PackageVersion(NamedTuple):
    hash: int
    name: str
    version: str
    release: str


class PackageTask(NamedTuple):
    task_id: int
    subtask_id: int
    branch: str
    hash: int
    name: str
    version: str
    release: str


class CveCpmHashes(NamedTuple):
    vuln_hash: int
    cpe_hash: int
    cpm_version_hash: int


class CveVersionsMatch(NamedTuple):
    id: str
    hashes: CveCpmHashes
    versions: CpeMatchVersions


class ErrataBuilder(APIWorker):
    """Handles Errata records modification."""

    def __init__(self, connection, branches: tuple[str, ...]):
        self.branches = branches
        self.conn = connection
        self.sql = SQL
        super().__init__()

    def _get_related_erratas_by_pkgs_names(
        self, packages: Iterable[str]
    ) -> dict[str, Errata]:
        self.status = False
        erratas = {}

        # collect erratas using package' names
        tmp_table = make_tmp_table_name("pkg_names")

        response = self.send_sql_request(
            self.sql.get_erratas_by_pkgs_names.format(
                branches=self.branches, tmp_table=tmp_table
            ),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("pkg_name", "String")],
                    "data": [{"pkg_name": n} for n in packages],
                },
            ],
        )
        if not self.sql_status:
            return {}
        for el in response:
            errata = Errata(
                id=ErrataID.from_id(el[0]),
                created=el[1],
                updated=el[2],
                hash=el[3],
                type=el[4],
                source=el[5],
                references=[Reference(t, l) for t, l in zip(el[6], el[7])],
                pkg_hash=el[8],
                pkg_name=el[9],
                pkg_version=el[10],
                pkg_release=el[11],
                pkgset_name=el[12],
                task_id=el[13],
                subtask_id=el[14],
                task_state=el[15],
                is_discarded=bool(el[17]),
            )
            erratas[errata.id.id] = errata  # type: ignore

        self.status = True
        return erratas

    def _get_related_erratas_by_cve_ids(
        self, cve_ids: Iterable[str]
    ) -> dict[str, Errata]:
        self.status = False
        erratas = {}

        tmp_table = make_tmp_table_name("cve_ids")

        response = self.send_sql_request(
            self.sql.get_erratas_by_cve_ids.format(
                branches=self.branches, tmp_table=tmp_table
            ),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("cve_id", "String")],
                    "data": [{"cve_id": c} for c in cve_ids],
                },
            ],
        )
        if not self.sql_status:
            return {}
        for el in response:
            errata = Errata(
                id=ErrataID.from_id(el[0]),
                created=el[1],
                updated=el[2],
                hash=el[3],
                type=el[4],
                source=el[5],
                references=[Reference(t, l) for t, l in zip(el[6], el[7])],
                pkg_hash=el[8],
                pkg_name=el[9],
                pkg_version=el[10],
                pkg_release=el[11],
                pkgset_name=el[12],
                task_id=el[13],
                subtask_id=el[14],
                task_state=el[15],
                is_discarded=bool(el[17]),
            )
            erratas[errata.id.id] = errata  # type: ignore

        self.status = True
        return erratas

    def _get_pkgs_versions(
        self, pkgs_hashes: Iterable[int]
    ) -> dict[int, PackageVersion]:
        self.status = False

        tmp_table = make_tmp_table_name("pkgs_hashes")

        response = self.send_sql_request(
            self.sql.get_packages_versions.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("pkg_hash", "UInt64")],
                    "data": [{"pkg_hash": h} for h in pkgs_hashes],
                },
            ],
        )
        if not self.sql_status or not response:
            return {}

        self.status = True
        return {p.hash: p for p in (PackageVersion(*el) for el in response)}

    def _get_pkgs_done_tasks(
        self, pkgs_names: Iterable[str]
    ) -> dict[str, list[PackageTask]]:
        self.status = False
        res: dict[str, list[PackageTask]] = {}

        tmp_table = make_tmp_table_name("pkgs_names")

        response = self.send_sql_request(
            self.sql.get_done_tasks_by_packages.format(
                branches=self.branches, tmp_table=tmp_table
            ),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("pkg_name", "String")],
                    "data": [{"pkg_name": n} for n in pkgs_names],
                },
            ],
        )
        if not self.sql_status or not response:
            return res

        for p in (PackageTask(*el) for el in response):
            res.setdefault(p.name, []).append(p)

        self.status = True
        return res

    def _get_cves_versions_matches(
        self, cve_cpm_hashes: Iterable[CveCpmHashes]
    ) -> dict[int, list[CveVersionsMatch]]:
        self.status = False
        res: dict[int, list[CveVersionsMatch]] = {}

        tmp_table = make_tmp_table_name("pkgs_hashes")

        response = self.send_sql_request(
            self.sql.get_cve_versions_matches.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [
                        ("vuln_hash", "UInt64"),
                        ("cpe_hash", "UInt64"),
                        ("cpm_version_hash", "UInt64"),
                    ],
                    "data": [e._asdict() for e in cve_cpm_hashes],
                },
            ],
        )
        if not self.sql_status or not response:
            return res

        for el in response:
            cvm = CveVersionsMatch(
                id=el[0],
                hashes=CveCpmHashes(*el[1:4]),
                versions=CpeMatchVersions(*el[4:]),
            )
            res.setdefault(cvm.hashes.vuln_hash, []).append(cvm)

        self.status = True
        return res

    def get_related_errata_records(
        self, *, packages: Iterable[str], cve_ids: Iterable[str]
    ) -> dict[str, Errata]:
        erratas = self._get_related_erratas_by_pkgs_names(packages)
        if not self.status:
            self.store_error({"message": "Failed to get erratas by package' names"})
            raise ErrataBuilderError("Failed to get erratas by package' names")

        _erratas = self._get_related_erratas_by_cve_ids(cve_ids)
        if not self.status:
            self.store_error({"message": "Failed to get erratas by CVE' IDs"})
            raise ErrataBuilderError("Failed to get erratas by CVE' IDs")
        erratas.update(**_erratas)

        return erratas

    def get_related_packages_tasks(self, pkgs_cve_matches: Iterable[PackageCveMatch]):
        # get packages versions
        pkgs_versions = self._get_pkgs_versions({m.pkg_hash for m in pkgs_cve_matches})
        if not self.status:
            self.store_error({"message": "Failed to get packages versions from DB"})
            raise ErrataBuilderError("Failed to get packages versions from DB")

        # get packages history
        pkgs_tasks = self._get_pkgs_done_tasks({m.pkg_name for m in pkgs_cve_matches})
        if not self.status:
            self.store_error({"message": "Failed to get packages tasks from DB"})
            raise ErrataBuilderError("Failed to get packages tasks from DB")

        # get CVE versions matches
        cve_cpm_versions = self._get_cves_versions_matches(
            {
                CveCpmHashes(m.vuln_hash, m.cpm_cpe_hash, m.cpm_version_hash)
                for m in pkgs_cve_matches
            }
        )
        if not self.status:
            raise ErrataBuilderError("Failed to get CVE versions matches from DB")

        errata_points = set()

        def pkg_is_vulnerable(pkg: PackageTask, cpm: CpeMatchVersions) -> bool:
            return version_less_or_equal(
                version1=pkg.version,
                version2=cpm.version_end,
                strictly_less=cpm.version_end_excluded,
            ) and version_less_or_equal(
                version1=cpm.version_start,
                version2=pkg.version,
                strictly_less=cpm.version_start_excluded,
            )

        class ErrataPoint(NamedTuple):
            task: PackageTask
            prev_task: Union[PackageTask, None]
            cvm: CveVersionsMatch

        # loop through matches and find possible errata creation point
        all_tasks = {}
        for t in (x for xx in pkgs_tasks.values() for x in xx):
            all_tasks.setdefault(t.branch, []).append(t)

        for match in (m for m in pkgs_cve_matches if not m.is_vulnerable):
            for cpm_ver in cve_cpm_versions.get(match.vuln_hash, []):
                if not all_tasks:
                    continue

                for tasks in all_tasks.values():
                    next_task = tasks[0]
                    # only one task found in history
                    if len(tasks) == 1:
                        errata_points.add(ErrataPoint(next_task, None, cpm_ver))
                        continue
                    # process task history
                    vulnerable_found = False
                    for t in tasks[1:]:
                        # skip tasks with package version is not vulnerable
                        if not pkg_is_vulnerable(t, cpm_ver.versions):
                            next_task = t
                            continue
                        # finally got vulnerable package version
                        errata_points.add(ErrataPoint(next_task, t, cpm_ver))
                        vulnerable_found = True
                        break
                    # use the oldest one task found in current branch as errata point
                    # candidate
                    if not vulnerable_found:
                        errata_points.add(ErrataPoint(tasks[-1], None, cpm_ver))

        return errata_points
