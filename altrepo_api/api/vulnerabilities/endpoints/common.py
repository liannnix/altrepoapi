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

import re
import json
import logging

from dataclasses import dataclass, asdict, field, replace
from datetime import datetime

from itertools import islice
from typing import Any, Iterable, Literal, NamedTuple, Protocol, Union

from altrepo_api.api.misc import lut
from altrepo_api.utils import make_tmp_table_name
from altrepo_api.libs.librpm_functions import (
    compare_versions,
    version_less_or_equal,
    VersionCompareResult,
)

from ..sql import SQL

logger = logging.getLogger(__name__)


ROOT_BRANCH = "sisyphus"
CVE_MATCHER_MAX_CPU = 4  # running more than 4 processes is inefficient
CVE_MATCHER_CHUNK_SIZE = 1000  # optimal chunk size is around 500-1000
BDU_ID_TYPE = "BDU"
BDU_ID_PREFIX = f"{BDU_ID_TYPE}:"
CVE_ID_TYPE = "CVE"
CVE_ID_PREFIX = f"{CVE_ID_TYPE}-"


def unescape(x: str) -> str:
    def first_pass(s: str) -> str:
        escaped = False
        current = ""

        for char in s:
            if escaped:
                current += char
                escaped = False
            elif char == "\\":
                escaped = True
            else:
                current += char

        return current

    x_ = first_pass(x)
    if not re.search(r"\\\W", x_):
        return x_
    else:
        return x_.replace("\\", "")


def chunks(data: dict[str, Any], size: int) -> Iterable[dict[str, Any]]:
    it = iter(data)
    for _ in range(0, len(data), size):
        yield {k: data[k] for k in islice(it, size)}


class PackageVersion(NamedTuple):
    hash: str
    name: str
    version: str
    release: str
    branch: str


class Task(NamedTuple):
    id: int
    branch: str
    package: str


class TaskState(NamedTuple):
    id: int
    state: str
    changed: datetime
    subtasks: set[int]


class CpeMatchVersions(NamedTuple):
    version_start: str
    version_end: str
    version_start_excluded: bool
    version_end_excluded: bool

    def asdict(self) -> dict[str, Any]:
        return self._asdict()


@dataclass(frozen=True)
class Errata:
    id: str
    ref_type: list[str]
    ref_link: list[str]
    branch: str
    task_id: int
    subtask_id: int
    task_state: str
    pkg_hash: str
    pkg_name: str
    pkg_version: str
    pkg_release: str

    def ref_ids(self, ref_type: Literal["bug", "vuln"]) -> list[str]:
        res = []

        for i in range(len(self.ref_type)):
            if self.ref_type[i] == ref_type:
                res.append(self.ref_link[i])

        return res

    def asdict(self) -> dict[str, Any]:
        res = asdict(self)
        del res["ref_type"]
        del res["ref_link"]
        res["vulns"] = [x for x in self.ref_link]
        return res

    def __hash__(self) -> int:
        return hash(json.dumps(self.asdict()))


@dataclass
class VulnerabilityInfo:
    id: str
    summary: str
    score: float
    severity: str
    url: str
    modified: datetime
    published: datetime
    json: dict[str, Any]
    refs_type: list[str]
    refs_link: list[str]

    def __post_init__(self):
        parsed = None

        try:
            parsed = json.loads(self.json)  # type: ignore
        except Exception:
            logger.debug(f"Failed to parse vulnerability JSON for {self.id}")
            pass

        if parsed is not None:
            self.json = parsed

    def asdict(self) -> dict[str, Any]:
        res = asdict(self)

        del res["refs_type"]
        del res["refs_link"]
        res["refs"] = [r for r in self.refs_link]

        return res


@dataclass
class CPE:
    part: str
    vendor: str
    product: str
    version: str
    update: str
    edition: str
    lang: str
    sw_edition: str
    target_sw: str
    target_hw: str
    other: str

    def __init__(self, cpe_str: str) -> None:
        res = re.split(r"(?<!\\):", cpe_str)
        (
            _,
            _,
            self.part,
            self.vendor,
            self.product,
            self.version,
            self.update,
            self.edition,
            self.lang,
            self.sw_edition,
            self.target_sw,
            self.target_hw,
            self.other,
        ) = res
        # self.vendor = unescape(self.vendor)
        # self.product = unescape(self.product)
        # self.version = unescape(self.version)
        # self.update = unescape(self.update)

    def __repr__(self) -> str:
        return (
            f"cpe:2.3:{self.part}:{self.vendor}:{self.product}:{self.version}:"
            f"{self.update}:{self.edition}:{self.lang}:{self.sw_edition}:"
            f"{self.target_sw}:{self.target_hw}:{self.other}"
        )


@dataclass
class CpeMatch:
    cpe: CPE
    version: CpeMatchVersions

    def __init__(self, cpe: str, *args) -> None:
        self.cpe = CPE(cpe)
        self.version = CpeMatchVersions(*args)

    def asdict(self) -> dict[str, Any]:
        return {"cpe": repr(self.cpe), "versions": self.version.asdict()}


class Vulnerability(NamedTuple):
    id: str
    cpe_matches: list[CpeMatch]

    def asdict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "cpe_matches": [cpem.asdict() for cpem in self.cpe_matches],
        }


@dataclass
class PackageVulnerabiltyInfo:
    name: str
    version: str
    release: str
    branch: str
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    fixed_in: set[Errata] = field(default_factory=set)

    def asdict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "release": self.release,
            "branch": self.branch,
            "vulneravilities": [v.asdict() for v in self.vulnerabilities],
            "fixed_in": [fix.asdict() for fix in self.fixed_in],
        }


def match_cpem_by_version(
    pkg: PackageVersion, cpems: Iterable[CpeMatch], debug: bool = False
) -> list[CpeMatch]:
    if not debug:
        return [
            cpem
            for cpem in cpems
            if version_less_or_equal(
                pkg.version,
                cpem.version.version_end,
                cpem.version.version_end_excluded,
            )
            and version_less_or_equal(
                cpem.version.version_start,
                pkg.version,
                cpem.version.version_start_excluded,
            )
        ]
    else:
        logger.debug(f"{pkg.name} {pkg.version}")
        res = []
        for cpem in cpems:
            if version_less_or_equal(
                pkg.version,
                cpem.version.version_end,
                cpem.version.version_end_excluded,
            ) and version_less_or_equal(
                cpem.version.version_start,
                pkg.version,
                cpem.version.version_start_excluded,
            ):
                res.append(cpem)
                logger.debug(f"Overlap: {cpem}")
            else:
                logger.debug(f"Not overlap: {cpem}")

        return res


@dataclass
class PackageVulnerability:
    hash: str
    name: str
    version: str
    release: str
    branch: str
    vuln_id: str
    vulnerable: bool = False
    fixed: bool = False
    cpe_matches: list[CpeMatch] = field(default_factory=list)
    fixed_in: list[Errata] = field(default_factory=list)

    def match_by_version(self, cpems: Iterable[CpeMatch]) -> "PackageVulnerability":
        self.cpe_matches = match_cpem_by_version(
            PackageVersion(
                hash="", name=self.name, version=self.version, release="", branch=""
            ),
            cpems,
        )
        self.vulnerable = len(self.cpe_matches) != 0

        return self

    def asdict(self) -> dict[str, Any]:
        res = asdict(self)
        res["cpe_matches"] = [cpem.asdict() for cpem in self.cpe_matches]
        res["fixed_in"] = [e.asdict() for e in self.fixed_in]
        return res

    def __hash__(self) -> int:
        return hash(json.dumps(self.asdict()))


def vulnerability_closed_in_errata(
    package: PackageVulnerability, errata: Errata
) -> bool:
    """Returns `true` if version in errata is less or equal to package's one."""
    return compare_versions(
        version1=errata.pkg_version,
        release1=errata.pkg_release,
        version2=package.version,
        release2=package.release,
    ) in (VersionCompareResult.LESS_THAN, VersionCompareResult.EQUAL)


# Protocols
class _pAPIWorker(Protocol):
    sql: SQL
    status: bool
    sql_status: bool
    logger: logging.Logger

    def store_error(
        self, message: dict[str, Any], severity: int = ..., http_code: int = ...
    ) -> tuple[Any, int]:
        ...

    def send_sql_request(
        self, request_line: Any, http_code: int = ..., **kwargs
    ) -> Any:
        ...


class _pHasBranch(Protocol):
    branch: str


class _pHasCveInfo(Protocol):
    cve_info: dict[str, VulnerabilityInfo]


class _pHasCveCpems(Protocol):
    cve_cpems: dict[str, list[CpeMatch]]


class _pHasErratas(Protocol):
    erratas: list[Errata]


class _pHasPackagesCpes(Protocol):
    packages_cpes: dict[str, list[CPE]]


class _pHasPackagesVersions(Protocol):
    packages_versions: list[PackageVersion]


class _pHasPackagesVulnerabilities(Protocol):
    packages_vulnerabilities: list[PackageVulnerability]


class _pGetErratasCompatible(_pHasErratas, _pHasBranch, _pAPIWorker, Protocol):
    ...


class _pDedupErratasCompatible(_pHasErratas, _pAPIWorker, Protocol):
    ...


class _pGetPackagesCpesCompatible(
    _pHasPackagesCpes, _pHasBranch, _pAPIWorker, Protocol
):
    ...


class _pGetCveInfoCompatible(
    _pHasCveInfo, _pHasCveCpems, _pHasBranch, _pAPIWorker, Protocol
):
    ...


class _pGetCveMatchingByPackageCpesCompatible(
    _pHasCveCpems,
    _pHasPackagesCpes,
    _pAPIWorker,
    Protocol,
):
    ...


class _pGetCveInfoByIdsCompatible(_pHasCveInfo, _pAPIWorker, Protocol):
    ...


class _pGetLastPackageVersionsCompatible(
    _pHasPackagesVersions,
    _pHasBranch,
    _pAPIWorker,
    Protocol,
):
    ...


class _pGetMatchedPackagesNamesCompatible(
    _pHasCveCpems,
    _pHasPackagesCpes,
    _pAPIWorker,
    Protocol,
):
    ...


class _pGetPackagesVulnerabilitiesCompatible(
    _pHasCveCpems,
    _pHasPackagesCpes,
    _pHasPackagesVersions,
    _pHasPackagesVulnerabilities,
    _pAPIWorker,
    Protocol,
):
    ...


class _pDedupPackagesVulnerabilitiesCompatible(
    _pHasPackagesVulnerabilities, _pAPIWorker, Protocol
):
    ...


class _pGetVulnerabilityFixErrataCompatible(
    _pHasPackagesVulnerabilities,
    _pHasPackagesVersions,
    _pHasErratas,
    _pHasBranch,
    _pAPIWorker,
    Protocol,
):
    ...


class _pGetTaskHistoryCompatible(_pHasBranch, _pAPIWorker, Protocol):
    ...


# Mixin
def _get_task_history(
    cls: _pGetTaskHistoryCompatible, pkg_names: Iterable[str]
) -> Union[dict[str, list[Task]], None]:
    """Find 'DONE' tasks by given package names and branch in accordance to
    task history and branch inheritance order."""

    cls.status = False

    if cls.branch not in lut.branch_inheritance:
        # nothing to do with it
        cls.status = True
        return None

    # use branches by inheritance
    branches = [cls.branch]
    branches += lut.branch_inheritance[cls.branch]

    tmp_table = make_tmp_table_name("pkg_names")
    external_tables = [
        {
            "name": tmp_table,
            "structure": [("pkg_name", "String")],
            "data": [{"pkg_name": n} for n in pkg_names],
        }
    ]

    # get 'DONE' tasks by package names and branches
    response = cls.send_sql_request(
        cls.sql.get_done_tasks_by_packages.format(
            branches=branches, tmp_table=tmp_table
        ),
        external_tables=external_tables,
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error({"message": "No 'DONE' tasks found in DB"})
        return None

    # ordered by 'task_changed' in descending order in SQL request
    tasks: dict[str, list[Task]] = {}
    for task in (Task(*el) for el in response):
        if task.package not in tasks:
            tasks[task.package] = []
        tasks[task.package].append(task)

    # collect all branches from found tasks
    _all_branches = set()

    # process tasks
    for package, _tasks in tasks.items():
        _branches = {t.branch for t in _tasks}
        _all_branches.update(_branches)

        # cut tasks list until the first task in given branch
        # we don't need them here due to errata history contents for
        # current branch is collected directly by packages names
        if cls.branch in _branches:
            i = 0
            for ii, t in enumerate(_tasks):
                if t.branch == cls.branch:
                    i = ii
            tasks[package] = _tasks[i:]

    if all(v == [] for v in tasks.values()):
        cls.status = True
        return None

    # collect all branches, including inherited from
    for b in tuple(_all_branches):
        _all_branches.update(lut.branch_inheritance.get(b, []))

    response = cls.send_sql_request(
        cls.sql.get_done_tasks_history.format(branches=tuple(_all_branches))
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error({"message": "No tasks history found in DB"})
        return None

    class TaskHistory(NamedTuple):
        id: int
        prev: int
        branch: str
        changed: datetime

    tasks_history = {t.id: t for t in (TaskHistory(*el) for el in response)}

    # get the map of latest task of each branch
    newest_tasks: dict[str, TaskHistory] = {}
    for task in tasks_history.values():
        if (
            task.branch not in newest_tasks
            or task.changed > newest_tasks[task.branch].changed
        ):
            newest_tasks[task.branch] = task

    branch_history: dict[str, set[int]] = {}

    # build the task and branch inheritance tree
    for branch, task in newest_tasks.items():
        t = task
        tasks_set = set()
        intermediate_branches = set()

        while True:
            tasks_set.add(t.id)

            if t.prev not in tasks_history:
                # End of the list
                break

            t = tasks_history[t.prev]

            if t.branch != branch and t.branch not in intermediate_branches:
                intermediate_branches.add(t.branch)

        branch_history[branch] = tasks_set

    # filter out packages tasks using branch history
    for package, _tasks in tasks.items():
        if not _tasks:
            continue

        _branch = _tasks[0].branch
        tasks[package] = [t for t in _tasks if t.id in branch_history[_branch]]

    cls.status = True
    return tasks


def _get_erratas(
    cls: _pGetErratasCompatible,
    where_clause: str,
    external_tables: list[dict[str, Any]] = [],
) -> None:
    cls.status = False

    # find errata by given `where_clause` and `external_tables` contents
    response = cls.send_sql_request(
        cls.sql.get_erratas.format(where_clause=where_clause),
        external_tables=external_tables,
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error({"message": "No errata records found in DB"})
        return None

    erratas = [Errata(*el[:-1]) for el in response]

    # get last task states
    # get last state for tasks in erratas
    task_states: dict[int, TaskState] = {}

    tmp_table = make_tmp_table_name("task_ids")

    response = cls.send_sql_request(
        cls.sql.get_last_tasks_state.format(tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("task_id", "UInt32")],
                "data": [{"task_id": e.task_id} for e in erratas],
            }
        ],
    )
    if not cls.sql_status:
        return None
    if response:
        task_states = {el[0]: TaskState(*el) for el in response}

    for errata in erratas:
        # filter out task related erratas
        if errata.task_id != 0:
            # XXX: task state info should be in DB!
            if errata.task_id not in task_states:
                cls.logger.warning(f"No task state data found for {errata.task_id}")
                continue

            ets = task_states[errata.task_id]
            # skip erratas from deleted tasks
            if ets.state not in ("DONE", "EPERM", "TESTED"):
                continue
            # skip erratas from deleted subtasks
            if errata.subtask_id not in ets.subtasks:
                cls.logger.debug(
                    f"Skip errata for task {ets.id} due to subtask {errata.subtask_id} deleted"
                )
                continue

        cls.erratas.append(errata)

    cls.status = True


def deduplicate_erratas(cls: _pDedupErratasCompatible) -> None:
    if not cls.erratas:
        return None

    cls.erratas = list(set(cls.erratas))


def deduplicate_packages_vulnerabilities(
    cls: _pDedupPackagesVulnerabilitiesCompatible,
) -> None:
    if not cls.packages_vulnerabilities:
        return None

    cls.packages_vulnerabilities = list(set(cls.packages_vulnerabilities))


def get_errata_by_cve_ids(cls: _pGetErratasCompatible, cve_ids: Iterable[str]) -> None:
    where_clause = (
        f"AND pkgset_name = '{cls.branch}'" f"AND hasAny(eh_references.link, {cve_ids})"
    )
    return _get_erratas(cls, where_clause)


def get_errata_by_pkg_names(
    cls: _pGetErratasCompatible, pkg_names: Iterable[str]
) -> None:
    tasks_history = _get_task_history(cls, pkg_names)
    # propagate error
    if not cls.status:
        return None

    # pass package names through external table
    tmp_table = make_tmp_table_name("pkg_names")
    external_tables = [
        {
            "name": tmp_table,
            "structure": [("pkg_name", "String")],
            "data": [{"pkg_name": n} for n in pkg_names],
        }
    ]

    where_clause = f"AND pkgset_name = '{cls.branch}' AND pkg_name IN {tmp_table}"

    if tasks_history is None:
        return _get_erratas(cls, where_clause, external_tables)

    task_ids = {t.id for tt in tasks_history.values() for t in tt}

    if not task_ids:
        return _get_erratas(cls, where_clause, external_tables)

    where_clause = (
        f"AND ((pkgset_name = '{cls.branch}' AND pkg_name IN {tmp_table}) OR "
    )

    tmp_table = make_tmp_table_name("task_ids")

    where_clause += f"(task_id IN {tmp_table} AND task_state = 'DONE'))"

    external_tables.append(
        {
            "name": tmp_table,
            "structure": [("task_id", "UInt32")],
            "data": [{"task_id": tid} for tid in task_ids],
        }
    )

    return _get_erratas(cls, where_clause, external_tables)


def get_cve_info(
    cls: _pGetCveInfoCompatible, cve_ids: Iterable[str], exclude_json: bool
) -> None:
    cls.status = False
    # 1. check if CVE info in DB
    tmp_table = make_tmp_table_name("vuiln_ids")

    if exclude_json:
        json_field = "'{}' AS vuln_json"
    else:
        json_field = "vuln_json"

    response = cls.send_sql_request(
        cls.sql.get_vuln_info_by_ids.format(tmp_table=tmp_table, json_field=json_field),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("vuln_id", "String")],
                "data": [{"vuln_id": cve_id} for cve_id in cve_ids],
            }
        ],
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error({"message": f"No CVE info found in DB for {cve_ids}"})
        return None

    cve_hashes: set[int] = set()
    for el in response:
        cve_hashes.add(el[0])
        cls.cve_info[el[1]] = VulnerabilityInfo(*el[1:])

    # 2. check if CPE matching is there
    tmp_table = make_tmp_table_name("vuiln_hashes")

    response = cls.send_sql_request(
        cls.sql.get_cves_cpe_matching.format(tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("vuln_hash", "UInt64")],
                "data": [{"vuln_hash": h} for h in cve_hashes],
            }
        ],
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error({"message": f"No CPE matches found in DB for {cve_ids}"})
        return None

    cls.cve_cpems = {el[0]: [CpeMatch(*x) for x in el[1]] for el in response}

    cls.status = True


def get_packages_cpes(
    cls: _pGetPackagesCpesCompatible, pkg_names: Iterable[str] = []
) -> None:
    cls.status = False

    cpe_branches = (lut.cpe_branch_map[cls.branch],)

    pkg_names_clause = ""
    external_tables = []
    if pkg_names:
        tmp_table = make_tmp_table_name("pkg_names")
        pkg_names_clause = f"WHERE pkg_name in {tmp_table}"
        external_tables = [
            {
                "name": tmp_table,
                "structure": [("pkg_name", "String")],
                "data": [{"pkg_name": n} for n in pkg_names],
            }
        ]

    response = cls.send_sql_request(
        cls.sql.get_packages_and_cpes.format(
            cpe_branches=cpe_branches, pkg_names_clause=pkg_names_clause
        ),
        external_tables=external_tables,
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error(
            {"message": f"No CPE matches data info found in DB for {cpe_branches}"}
        )
        return None

    for pkg_name, cpe in response:
        if pkg_name not in cls.packages_cpes:
            cls.packages_cpes[pkg_name] = []
        try:
            cls.packages_cpes[pkg_name].append(CPE(cpe))
        except ValueError:
            cls.logger.warning(f"Failed to parse CPE {cpe} for {pkg_name}")

    cls.status = True


def get_last_packages_versions(
    cls: _pGetLastPackageVersionsCompatible, pkg_names: Iterable[str]
) -> None:
    cls.status = False

    branches = (cls.branch,)

    tmp_table = make_tmp_table_name("pkg_names")

    response = cls.send_sql_request(
        cls.sql.get_packages_versions.format(branches=branches, tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("pkg_name", "String")],
                "data": [{"pkg_name": p} for p in pkg_names],
            }
        ],
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error({"message": "No packages data found in DB"})
        return None

    cls.packages_versions = [PackageVersion(*el) for el in response]
    cls.status = True


def get_matched_packages_names(cls: _pGetMatchedPackagesNamesCompatible) -> list[str]:
    cve_cpe_triplets = {
        (cpem.cpe.vendor, cpem.cpe.product, cpem.cpe.target_sw)
        for cpems in cls.cve_cpems.values()
        for cpem in cpems
    }

    return list(
        {
            pkg
            for pkg, cpes in cls.packages_cpes.items()
            for cpe in cpes
            if (cpe.vendor, cpe.product, cpe.target_sw) in cve_cpe_triplets
        }
    )


def matcher(
    cve_cpems: dict[str, list[CpeMatch]],
    packages_versions: list[PackageVersion],
    packages_cpes: dict[str, list[CPE]],
) -> list[PackageVulnerability]:
    """Build package vulnerabilites objects by CPE matching."""

    result = []

    class CveMatch(NamedTuple):
        vuln_id: str
        cpms: list[CpeMatch]

    class PkgMatch(NamedTuple):
        version: PackageVersion
        cpes: list[CPE]

    CPETriplet = tuple[str, str, str]

    def cpe_triplet(cpe: CPE) -> CPETriplet:
        return (cpe.vendor, cpe.product, cpe.target_sw)

    # build-up CVE' CPE matches related data structures
    cve_matches = tuple(
        [CveMatch(vuln_id, cpems) for vuln_id, cpems in cve_cpems.items()]
    )
    # reverse index
    cves_cpe_ridx: dict[CPETriplet, list[int]] = {}
    for idx, cvem in enumerate(cve_matches):
        for cpem in cvem.cpms:
            triplet = cpe_triplet(cpem.cpe)
            if triplet in cves_cpe_ridx:
                cves_cpe_ridx[triplet].append(idx)
            else:
                cves_cpe_ridx[triplet] = [idx]

    # loop through data using indexes
    for idx, pkgm in enumerate(
        pkgm
        for pkgm in (
            PkgMatch(pkg, packages_cpes.get(pkg.name, [])) for pkg in packages_versions
        )
        if pkgm.cpes
    ):
        #  collect related CVE's
        pkg_cpe_triplets = {cpe_triplet(cpe) for cpe in pkgm.cpes}

        related_cves_idxs: set[int] = set()
        for idxs in (cves_cpe_ridx[t] for t in pkg_cpe_triplets if t in cves_cpe_ridx):
            related_cves_idxs.update(idxs)

        for cvem in (cve_matches[idx] for idx in sorted(related_cves_idxs)):
            result.append(
                PackageVulnerability(
                    **pkgm.version._asdict(), vuln_id=cvem.vuln_id
                ).match_by_version(
                    (
                        cpem
                        for cpem in cvem.cpms
                        if cpe_triplet(cpem.cpe) in pkg_cpe_triplets
                    )
                )
            )

    return result


def get_packages_vulnerabilities(cls: _pGetPackagesVulnerabilitiesCompatible) -> None:
    cls.status = False

    cls.logger.debug(f"Starting packages CVE matching: {datetime.now()}")
    cls.logger.debug(f"CVE objects count: {len(cls.cve_cpems)}")
    cls.logger.debug(f"Packages count: {len(cls.packages_versions)}")
    cls.logger.debug(
        f"Total CPE matches count: {len([c for cpems in cls.cve_cpems.values() for c in cpems])}"
    )

    matched = matcher(cls.cve_cpems, cls.packages_versions, cls.packages_cpes)
    cls.logger.debug(f"Matched packages vulnerabilities: {len(matched)}")
    cls.packages_vulnerabilities.extend(matched)
    cls.logger.debug(f"Packages CVE matching finished: {datetime.now()}")

    cls.packages_vulnerabilities = sorted(
        cls.packages_vulnerabilities,
        key=lambda x: (x.branch, x.vuln_id, x.vulnerable, x.name, x.version),
    )

    cls.status = True


def get_vulnerability_fix_errata(
    cls: _pGetVulnerabilityFixErrataCompatible, cve_ids: Iterable[str]
) -> None:
    cls.status = False

    # process packages vulnerabilities found by CPE and version matching
    if cls.packages_vulnerabilities:
        # check found erratas for vulnerability fixes
        for pkg in cls.packages_vulnerabilities:
            # skip packages that not vulnerable by CPE match version comparison
            if not pkg.vulnerable:
                continue

            for errata in cls.erratas:
                if (pkg.name, pkg.branch) == (
                    errata.pkg_name,
                    errata.branch,
                ) and pkg.vuln_id in errata.ref_ids(ref_type="vuln"):
                    # no need to check version due to branch, package name and vulnerability id is equal already
                    pkg.fixed_in.append(errata)

            # if package in taskless branch and found any errata mark it as `fixed` and continue
            if pkg.fixed_in and pkg.branch in lut.taskless_branches:
                pkg.fixed = True
                pkg.vulnerable = False
                continue

            for errata in pkg.fixed_in:
                # set `fixed` flag if task is `DONE` and update task state of errata
                if errata.task_state == "DONE":
                    pkg.fixed = True
                    pkg.vulnerable = False

    # update results with packages found by errata history matching
    cve_ids_set = set(cve_ids)

    known_erratas = {
        (e.branch, e.task_id, e.pkg_name, e.pkg_version, e.pkg_release)
        for v in cls.packages_vulnerabilities
        for e in v.fixed_in
    }

    vulnerable_packages = {
        (p.name, p.version, p.release, p.vuln_id)
        for p in cls.packages_vulnerabilities
        if p.vulnerable
    }

    pv_list: list[PackageVulnerability] = []

    for errata in cls.erratas:
        # skip known erratas if any
        if (
            errata.branch,
            errata.task_id,
            errata.pkg_name,
            errata.pkg_version,
            errata.pkg_release,
        ) in known_erratas:
            continue

        # build package vulnerability from errata and last package version
        for pkg in cls.packages_versions:
            # XXX: do not match branch here to handle erratas from parent branches
            # if (pkg.branch, pkg.name) == (errata.branch, errata.pkg_name):
            if pkg.name == errata.pkg_name:
                # get any vuln_id if it is linked with errata
                vuln_ids = cve_ids_set.intersection(set(errata.ref_ids("vuln")))
                if not vuln_ids:
                    continue

                pv = PackageVulnerability(
                    **pkg._asdict(),
                    vuln_id="",
                    vulnerable=True,
                    fixed=False,
                    fixed_in=[errata],
                )
                if compare_versions(
                    version1=pkg.version,
                    release1=pkg.release,
                    version2=errata.pkg_version,
                    release2=errata.pkg_release,
                ) in (VersionCompareResult.EQUAL, VersionCompareResult.GREATER_THAN):
                    pv.vulnerable = False
                    if (
                        errata.task_state == "DONE"
                        or errata.branch in lut.taskless_branches
                    ):
                        pv.fixed = True

                # add PackageVulnerability record for every CVE id mentioned in errata
                for vuln_id in vuln_ids:
                    # skip vulnerabilities marked as not vulnerable
                    if (
                        pkg.name,
                        pkg.version,
                        pkg.release,
                        vuln_id,
                    ) not in vulnerable_packages:
                        continue
                    # XXX: make a copy of dataclass object instance here!
                    pv_ = replace(pv, vuln_id=vuln_id)
                    pv_list.append(pv_)
                break

    # update found packages vulnerabilities
    # 1. sort pv_list
    pv_list.sort(key=lambda x: (x.branch, x.vuln_id, x.vulnerable, x.name, x.version))

    # 2. remove duplicated elements from results
    def pv2cmp_tuple(pv: PackageVulnerability) -> tuple[Any, ...]:
        return (pv.hash, pv.name, pv.version, pv.release, pv.branch, pv.vuln_id)

    # FIXME: update here erases `cpe_matches` from original `packages_vulnerabilities` list
    for pv in [
        pv
        for pv in cls.packages_vulnerabilities
        if (pv.vulnerable is True and pv.fixed is False)
    ]:
        for errata_pv in pv_list:
            if pv2cmp_tuple(pv) == pv2cmp_tuple(errata_pv):
                try:
                    cls.packages_vulnerabilities.remove(pv)
                except ValueError:
                    pass

    cls.packages_vulnerabilities.extend(pv_list)
    cls.status = True


def get_cve_matching_by_cpes(cls: _pGetCveMatchingByPackageCpesCompatible) -> None:
    cls.status = False

    # get CVE CPE matching by packages CPEs
    tmp_table = make_tmp_table_name("cpm_cpes")

    response = cls.send_sql_request(
        cls.sql.get_cves_cpems_by_cpe.format(tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("cpe_cpm", "String")],
                "data": [
                    {"cpe_cpm": str(cpe)}
                    for cpes in cls.packages_cpes.values()
                    for cpe in cpes
                ],
            }
        ],
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error({"message": "No CPE matches data info found in DB"})
        return None

    cls.cve_cpems = {el[0]: [CpeMatch(*x) for x in el[1]] for el in response}

    cls.status = True


def get_cve_info_by_ids(
    cls: _pGetCveInfoByIdsCompatible, cve_ids: Iterable[str], exclude_json: bool
) -> None:
    cls.status = False

    tmp_table = make_tmp_table_name("vuiln_ids")

    if exclude_json:
        json_field = "'{}' AS vuln_json"
    else:
        json_field = "vuln_json"

    response = cls.send_sql_request(
        cls.sql.get_vuln_info_by_ids.format(tmp_table=tmp_table, json_field=json_field),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("vuln_id", "String")],
                "data": [{"vuln_id": cve_id} for cve_id in cve_ids],
            }
        ],
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error({"message": f"No CVE data info found in DB for {cve_ids}"})
        return None

    for el in response:
        cls.cve_info[el[1]] = VulnerabilityInfo(*el[1:])

    cls.status = True
