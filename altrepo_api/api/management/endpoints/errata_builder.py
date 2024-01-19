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
from datetime import datetime
from typing import Any, Iterable, NamedTuple, Optional, Union
from uuid import UUID

from altrepodb_libs import (
    PackageCveMatch,
    VersionCompareResult,
    version_compare,
    version_less_or_equal,
)

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.api.vulnerabilities.endpoints.common import CpeMatchVersions

from altrepo_api.utils import make_tmp_table_name

from .manage import ManageErrata
from .tools.base import Errata, ErrataID, Reference, UserInfo
from .tools.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_UPDATE,
    CHANGE_SOURCE_KEY,
    CHANGE_SOURCE_AUTO,
    CVE_ID_TYPE,
    DT_NEVER,
    DRY_RUN_KEY,
    TASK_STATE_DONE,
    TASK_PACKAGE_ERRATA_TYPE,
    TASK_PACKAGE_ERRATA_SOURCE,
    VULN_REFERENCE_TYPE,
)
from .tools.changelog import (
    ChangelogRecord,
    PackageChangelog,
    split_evr,
    vulns_from_pkg_changelog,
)
from .tools.errata import errata_hash


ERRATA_MANAGE_RESPONSE_ERRATA_FIELD = "errata"
ERRATA_MANAGE_RESPONSE_ERRATA_CHANGE_FIELD = "errata_change"


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
    pkg_release,
    pkgset_name
FROM static_last_packages
WHERE pkg_hash IN {tmp_table}
    AND pkg_sourcepackage = 1
"""

    get_packages_changelogs = """
WITH package_changelog AS
    (
        SELECT
            pkg_hash,
            pkg_changelog.date AS date,
            pkg_changelog.name as name,
            pkg_changelog.evr AS evr,
            pkg_changelog.hash AS hash
        FROM Packages
ARRAY JOIN pkg_changelog
        PREWHERE pkg_hash IN (SELECT * FROM {tmp_table})
    )
SELECT DISTINCT
    pkg_hash,
    date,
    name,
    evr,
    Chg.chlog_text as text
FROM package_changelog
LEFT JOIN
(
    SELECT DISTINCT
        chlog_hash AS hash,
        chlog_text
    FROM Changelog
    WHERE chlog_hash IN (
        SELECT hash
        FROM package_changelog
    )
) AS Chg ON Chg.hash = package_changelog.hash
"""

    get_done_tasks = """
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
    {where_clause}
    ORDER BY task_changed DESC
)
SELECT DISTINCT
    task_id,
    subtask_id,
    pkgset_name,
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    task_changed
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

    get_done_tasks_by_packages_clause = """
WHERE pkgset_name in {branches}
    AND pkg_name IN {tmp_table}
    AND pkg_sourcepackage = 1
    AND tplan_action = 'add'
"""

    get_done_tasks_by_nevr_cluse = """
WHERE pkgset_name in {branches}
    AND pkg_name = '{name}'
    AND pkg_epoch = {epoch}
    AND pkg_version = '{version}'
    AND pkg_release = '{release}'
    AND pkg_sourcepackage = 1
    AND tplan_action = 'add'
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

    get_bdus_by_cves = """
SELECT
    vuln_id,
    vuln_references.type,
    vuln_references.link
FROM Vulnerabilities
WHERE (vuln_id, vuln_hash) IN (
    SELECT
        vuln_id,
        argMax(vuln_hash, ts)
    FROM Vulnerabilities
    WHERE vuln_id IN (
        SELECT vuln_id
        FROM Vulnerabilities
        WHERE arrayExists(x -> (x IN {tmp_table}), `vuln_references.link`)
    )
    GROUP BY vuln_id
)
"""


class PackageVersion(NamedTuple):
    hash: int
    name: str
    version: str
    release: str
    branch: str


class PackageTask(NamedTuple):
    task_id: int
    subtask_id: int
    branch: str
    hash: int
    name: str
    version: str
    release: str
    changed: datetime


class CveCpmHashes(NamedTuple):
    vuln_hash: int
    cpe_hash: int
    cpm_version_hash: int


class CveVersionsMatch(NamedTuple):
    id: str
    hashes: CveCpmHashes
    versions: CpeMatchVersions


class ErrataPoint(NamedTuple):
    task: PackageTask
    prev_task: Union[PackageTask, None]
    cvm: CveVersionsMatch


def branch_inheritance_list(b: str) -> dict[str, int]:
    if b not in lut.branch_inheritance:
        return {lut.branch_inheritance_root: 0}

    if b == lut.branch_inheritance_root:
        return {b: 0}

    return {x: i for i, x in enumerate([b] + lut.branch_inheritance[b])}


def collect_erratas(
    task: PackageTask, erratas_by_package: dict[str, list[Errata]]
) -> list[Errata]:
    # filter out existing erratas by package name and branch using
    # branch inheratance list
    return [
        e
        for e in erratas_by_package.get(task.name, [])
        if e.pkgset_name in branch_inheritance_list(task.branch)
    ]


def find_errata_by_pkg_task(t: PackageTask, erratas: list[Errata]) -> Optional[Errata]:
    for e in erratas:
        # got existing errata
        if (e.task_id, e.pkg_version, e.pkg_release) == (
            t.task_id,
            t.version,
            t.release,
        ):
            return e
    return None


def cve_in_errata_references(cve_id: str, e: Errata) -> bool:
    return cve_id in (r.link for r in e.references)


def get_closest_task(
    branch: str, tasks: dict[str, list[PackageTask]]
) -> Union[PackageTask, None]:
    for b in branch_inheritance_list(branch).keys():
        if b in tasks and tasks[b]:
            return tasks[b][0]


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


def version_release_compare(
    *, v1: str, r1: str, v2: str, r2: str
) -> VersionCompareResult:
    return version_compare(version1=f"{v1}-{r1}", version2=f"{v2}-{r2}")


class ErrataBuilder(APIWorker):
    """Handles Errata records modification."""

    def __init__(self, connection, branches: tuple[str, ...]):
        self.branches = branches
        self.conn = connection
        self.sql = SQL
        super().__init__()

    def _get_related_erratas_by_pkgs_names(
        self, packages: Iterable[str], exclude_discarded: bool
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
            # XXX: skip discarded erratas here
            if exclude_discarded and errata.is_discarded:
                continue
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

    def _get_pkgs_changelog(
        self, pkgs_hashes: Iterable[int]
    ) -> dict[int, PackageChangelog]:
        res: dict[int, PackageChangelog] = {}
        self.status = False

        tmp_table = make_tmp_table_name("pkgs_hashes")

        response = self.send_sql_request(
            self.sql.get_packages_changelogs.format(tmp_table=tmp_table),
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

        for el in response:
            if el[0] not in res:
                res[el[0]] = PackageChangelog(el[0], list())
            res[el[0]].changelog.append(ChangelogRecord(*el[1:]))

        self.status = True
        return res

    def _get_build_tasks_by_pkg_nevr(
        self, name: str, evr: str
    ) -> dict[str, list[PackageTask]]:
        """Returns dict[branch, list[PackageTask]] for given package' name and evr."""

        self.status = False
        res: dict[str, list[PackageTask]] = {}

        epoch, version, release = split_evr(evr)

        where_clause = self.sql.get_done_tasks_by_nevr_cluse.format(
            branches=self.branches,
            name=name,
            epoch=epoch,
            version=version,
            release=release,
        )

        response = self.send_sql_request(
            self.sql.get_done_tasks.format(where_clause=where_clause)
        )
        if not self.sql_status:
            return res

        for p in (PackageTask(*el) for el in response):
            res.setdefault(p.branch, []).append(p)

        self.status = True
        return res

    def _get_pkgs_done_tasks(
        self, pkgs_names: Iterable[str]
    ) -> dict[str, list[PackageTask]]:
        """Returns dict[name, list[PackageTask]] for given packages names."""

        self.status = False
        res: dict[str, list[PackageTask]] = {}

        tmp_table = make_tmp_table_name("pkgs_names")

        where_clause = self.sql.get_done_tasks_by_packages_clause.format(
            branches=self.branches, tmp_table=tmp_table
        )

        response = self.send_sql_request(
            self.sql.get_done_tasks.format(where_clause=where_clause),
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

    def _get_possible_errata_points(
        self,
        pkgs_cve_matches: Iterable[PackageCveMatch],
        pkgs_versions: dict[int, PackageVersion],
    ) -> set[ErrataPoint]:
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

        # loop through matches and find possible errata creation point
        all_tasks: dict[str, list[PackageTask]] = {}
        for t in (x for xx in pkgs_tasks.values() for x in xx):
            all_tasks.setdefault(t.branch, []).append(t)

        for match_ in (m for m in pkgs_cve_matches if not m.is_vulnerable):
            # check if any tasks found for package in a given branch
            if not all_tasks.get(pkgs_versions[match_.pkg_hash].branch):
                continue

            for cpm_ver in cve_cpm_versions.get(match_.vuln_hash, []):
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

    def build_erratas_on_cpe_add(
        self, pkgs_cve_matches: list[PackageCveMatch]
    ) -> tuple[list[ErrataPoint], list[tuple[Errata, str]]]:
        if not pkgs_cve_matches:
            self.logger.info("No packages' CVE matches found to be processed")
            return [], []

        # collect affected packages names and hashes
        pkgs_names = {m.pkg_name for m in pkgs_cve_matches}
        pkgs_hashes = {m.pkg_hash for m in pkgs_cve_matches}

        # get packages versions
        pkgs_versions = self._get_pkgs_versions(pkgs_hashes)
        print("DBG", pkgs_hashes)
        if not self.status:
            self.store_error({"message": "Failed to get packages versions from DB"})
            raise ErrataBuilderError("Failed to get packages versions from DB")

        # get existing erratas by packages names
        all_erratas = self._get_related_erratas_by_pkgs_names(
            packages=pkgs_names, exclude_discarded=True
        )
        if not self.status:
            self.store_error({"message": "Failed to get erratas by package' names"})
            raise ErrataBuilderError("Failed to get erratas by package' names")

        erratas_by_package: dict[str, list[Errata]] = {}

        # build existing errata mapping
        for errata in all_erratas.values():
            erratas_by_package.setdefault(errata.pkg_name, list()).append(errata)

        erratas_for_update: list[tuple[Errata, str]] = []
        erratas_for_create: list[ErrataPoint] = []

        # look for possible errata creation points
        possible_errata_points = self._get_possible_errata_points(
            pkgs_cve_matches, pkgs_versions
        )

        if not possible_errata_points:
            self.logger.debug(
                f"No possible errata creation points found for {pkgs_names}"
            )
            return [], []

        # get packages changelogs
        pkgs_changelogs = self._get_pkgs_changelog(
            {ep.task.hash for ep in possible_errata_points}
        )
        if not self.status:
            self.store_error({"message": "Failed to get packages changelogs from DB"})
            raise ErrataBuilderError("Failed to get packages changelogs from DB")

        # loop through possible errata points
        for ep in possible_errata_points:
            # collect existing erratas by package name and branch
            existing_erratas = collect_erratas(ep.task, erratas_by_package)
            exact_errata = find_errata_by_pkg_task(ep.task, existing_erratas)
            # got existing errata to be updated
            if exact_errata is not None:
                # CVE ID already in existintg errata for given package
                if cve_in_errata_references(ep.cvm.id, exact_errata):
                    continue
                # collect errata for update and continue
                self.logger.debug(
                    f"Found exact errata to be updated: {ep.cvm.id}: {exact_errata}"
                )
                erratas_for_update.append((exact_errata, ep.cvm.id))
                continue
            # check exiting erratas history for CVE was closed already
            closing_errata_found = False
            for errata in existing_erratas:
                if not cve_in_errata_references(ep.cvm.id, errata):
                    # skip errata that not contains given CVE
                    continue
                # 1. errata branch matches and package version-release is less or equal
                if version_release_compare(
                    v1=errata.pkg_version,
                    r1=errata.pkg_release,
                    v2=ep.task.version,
                    r2=ep.task.release,
                ) in (VersionCompareResult.EQUAL, VersionCompareResult.LESS_THAN):
                    if errata.pkgset_name == ep.task.branch:
                        # found errata that closes given CVE in current branch
                        closing_errata_found = True
                        self.logger.debug(
                            f"Found errata that closes {ep.cvm.id} in branch {ep.task.branch}: {errata}"
                        )
                        continue
                    else:
                        # found errata that closes given CVE in current branch inheritance list
                        closing_errata_found = True
                        self.logger.debug(
                            f"Found errata that closes {ep.cvm.id} for branch {ep.task.branch}: {errata}"
                        )
                        continue
            if closing_errata_found:
                continue
            # XXX: no erratas were found that closes given CVE
            # 1. check package changelog to clarify exact errata creation point
            ep_found = False
            pkg_changelog = pkgs_changelogs[ep.task.hash]

            for chlog, vulns in zip(
                pkg_changelog.changelog, vulns_from_pkg_changelog(pkg_changelog)
            ):
                # TODO: in fact there should be existing errata for CVEs that are closed by changelog
                if ep.cvm.id in vulns:
                    # found exact changelog record that closes given CVE
                    task = get_closest_task(
                        ep.task.branch,
                        self._get_build_tasks_by_pkg_nevr(ep.task.name, chlog.evr),
                    )
                    if task:
                        _ep = ErrataPoint(task=task, prev_task=None, cvm=ep.cvm)
                        erratas_for_create.append(_ep)
                        self.logger.debug(
                            f"Found most suitable errata point for {ep.cvm.id} in {ep.task.branch}: {_ep}"
                        )
                        ep_found = True
                        break
            if ep_found:
                continue
            # 2. nothing suitable was found, so use found task to create new errata record
            self.logger.debug(
                f"use errata point for {ep.cvm.id} in {ep.task.branch}: {ep}"
            )
            erratas_for_create.append(ep)

        return erratas_for_create, erratas_for_update


def build_em_payload(
    user_info: UserInfo, action: str, errata: Errata, transaction_id: UUID
) -> dict[str, Any]:
    return {
        "user": user_info.name,
        "reason": f"Errata changed due to: {user_info.reason} [{transaction_id}]",
        "action": action,
        "errata": errata.asdict(),
    }


def build_validation_error_report(worker: APIWorker, args: Any) -> dict[str, Any]:
    return {
        "message": "Request parameters validation error",
        "args": args,
        "details": worker.validation_results,
    }


class ErrataHandler(APIWorker):
    """Handles Errata records modification."""

    def __init__(
        self, connection, user_info: UserInfo, transaction_id: UUID, dry_run: bool
    ):
        self.transaction_id = transaction_id
        self.user_info = user_info
        self.dry_run = dry_run
        self.conn = connection
        self.sql = SQL
        self.errata_records: list[dict[str, Any]] = []
        self.errata_change_records: list[dict[str, Any]] = []
        super().__init__()

    def _get_bdus_by_cves(self, cve_ids: Iterable[str]) -> dict[str, set[str]]:
        self.status = False
        bdus_by_cve: dict[str, set[str]] = {}

        tmp_table = make_tmp_table_name("cve_ids")

        response = self.send_sql_request(
            self.sql.get_bdus_by_cves.format(tmp_table=tmp_table),
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
            bdu_id = el[0]
            for reference in (Reference(t, l) for t, l in zip(el[1], el[2])):
                if reference.type != CVE_ID_TYPE:
                    continue
                bdus_by_cve.setdefault(reference.link, set()).add(bdu_id)

        self.status = True
        return bdus_by_cve

    def _build_erratas_update(
        self,
        erratas_for_update: list[tuple[Errata, str]],
        bdus_by_cve: dict[str, set[str]],
    ) -> list[Errata]:
        # updates erratas with new CVE and related BDU IDs
        erratas: dict[str, Errata] = {}

        for errata, cve_id in erratas_for_update:
            # update existing errata if several CVE ids are added to the same one
            _errata_id = errata.id.id  # type: ignore
            _errata = erratas.get(_errata_id, errata)
            _references = _errata.references
            _linked_vulns = {r.link for r in _references}

            # append new CVE reference if not exists
            if cve_id not in _linked_vulns:
                _references.append(Reference(VULN_REFERENCE_TYPE, cve_id))
            # append new BDU references if not exists
            for bdu_id in bdus_by_cve.get(cve_id, set()):
                if bdu_id not in _linked_vulns:
                    _references.append(Reference(VULN_REFERENCE_TYPE, bdu_id))

            _errata = _errata.update(references=sorted(_references))
            erratas[_errata_id] = _errata.update(hash=errata_hash(_errata))

        return list(erratas.values())

    def _build_erratas_create(
        self, erratas_for_create: list[ErrataPoint], bdus_by_cve: dict[str, set[str]]
    ) -> list[Errata]:
        erratas = []

        for ep in erratas_for_create:
            cve_id = ep.cvm.id
            _references = [Reference(VULN_REFERENCE_TYPE, cve_id)]
            for bdu_id in bdus_by_cve.get(cve_id, set()):
                _references.append(Reference(VULN_REFERENCE_TYPE, bdu_id))

            _references = sorted(_references)

            errata = Errata(
                id=None,
                type=TASK_PACKAGE_ERRATA_TYPE,
                source=TASK_PACKAGE_ERRATA_SOURCE,
                created=DT_NEVER,
                updated=DT_NEVER,
                pkg_hash=ep.task.hash,
                pkg_name=ep.task.name,
                pkg_version=ep.task.version,
                pkg_release=ep.task.release,
                pkgset_name=ep.task.branch,
                task_id=ep.task.task_id,
                subtask_id=ep.task.subtask_id,
                task_state=TASK_STATE_DONE,
                references=_references,
                hash=0,
                is_discarded=False,
            )
            erratas.append(errata.update(hash=errata_hash(errata)))

        return erratas

    def _create_errata(self, errata: Errata) -> tuple[bool, dict[str, Any]]:
        args = {
            "payload": build_em_payload(
                self.user_info, CHANGE_ACTION_CREATE, errata, self.transaction_id
            ),
            "transaction_id": self.transaction_id,
            DRY_RUN_KEY: self.dry_run,
            CHANGE_SOURCE_KEY: CHANGE_SOURCE_AUTO,
        }
        me = ManageErrata(connection=self.conn, **args)
        # validate input
        if not me.check_params_post():
            return False, build_validation_error_report(me, args)
        # process errata changes
        response, http_code = me.post()
        return http_code == 200, response

    def _update_errata(self, errata: Errata) -> tuple[bool, dict[str, Any]]:
        args = {
            "payload": build_em_payload(
                self.user_info, CHANGE_ACTION_UPDATE, errata, self.transaction_id
            ),
            "transaction_id": self.transaction_id,
            DRY_RUN_KEY: self.dry_run,
            CHANGE_SOURCE_KEY: CHANGE_SOURCE_AUTO,
        }
        me = ManageErrata(connection=self.conn, **args)
        # validate input
        if not me.check_params_put():
            return False, build_validation_error_report(me, args)
        # process errata changes
        response, http_code = me.put()
        return http_code == 200, response

    def commit(
        self,
        erratas_for_create: list[ErrataPoint],
        erratas_for_update: list[tuple[Errata, str]],
    ) -> None:
        # collect CVE to BDUs mapping
        cve_ids = {cve_id for _, cve_id in erratas_for_update}
        cve_ids.update({p.cvm.id for p in erratas_for_create})

        bdus_by_cve = self._get_bdus_by_cves(cve_ids)
        if not self.status:
            raise ErrataBuilderError("Failed to get BDUs by CVEs")

        for errata in self._build_erratas_update(erratas_for_update, bdus_by_cve):
            status, result = self._update_errata(errata)
            if not status:
                self.store_error(
                    {
                        "message": f"Failed to update Errata in DB: {errata.id}",
                        "details": result,
                    },
                    severity=self.LL.ERROR,
                    http_code=400,
                )
                raise ErrataBuilderError("Failed to update Errata")
            self.errata_records.extend(
                result.get(ERRATA_MANAGE_RESPONSE_ERRATA_FIELD, [])
            )
            self.errata_change_records.extend(
                result.get(ERRATA_MANAGE_RESPONSE_ERRATA_CHANGE_FIELD, [])
            )

        for errata in self._build_erratas_create(erratas_for_create, bdus_by_cve):
            status, result = self._create_errata(errata)
            if not status:
                self.store_error(
                    {
                        "message": (
                            "Failed to create Errata in DB for : "
                            f"{errata.task_id}.{errata.subtask_id} : {errata.pkg_name}"
                        ),
                        "details": result,
                    },
                    severity=self.LL.ERROR,
                    http_code=400,
                )
                raise ErrataBuilderError("Failed to update Errata")
            self.errata_records.extend(
                result.get(ERRATA_MANAGE_RESPONSE_ERRATA_FIELD, [])
            )
            self.errata_change_records.extend(
                result.get(ERRATA_MANAGE_RESPONSE_ERRATA_CHANGE_FIELD, [])
            )
