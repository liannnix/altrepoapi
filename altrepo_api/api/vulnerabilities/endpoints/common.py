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

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Iterable, Literal, NamedTuple, Protocol, Union

from altrepo_api.api.misc import lut
from altrepo_api.utils import make_tmp_table_name
from altrepo_api.libs.librpm_functions import compare_versions, version_less_or_equal

from ..sql import SQL

logger = logging.getLogger(__name__)


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


class PackageVersion(NamedTuple):
    hash: str
    name: str
    version: str
    release: str
    branch: str


@dataclass
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

    def asdict(self, strip_json: bool = True) -> dict[str, Any]:
        res = asdict(self)

        del res["refs_type"]
        del res["refs_link"]
        res["refs"] = [r for r in self.refs_link]

        if strip_json:
            del res["json"]
        return res


@dataclass
class CpeMatchVersions:
    version_start: str
    version_end: str
    version_start_excluded: bool
    version_end_excluded: bool


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
        return asdict(self)


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
        res["cpe_matches"] = [
            {"cpe": repr(cpem.cpe), "versions": asdict(cpem.version)}
            for cpem in self.cpe_matches
        ]
        res["fixed_in"] = [e.asdict() for e in self.fixed_in]
        return res


def vulnerability_closed_in_errata(
    package: PackageVulnerability, errata: Errata
) -> bool:
    """Returns `true` if version in errata is less or equal to package's one."""
    return (
        compare_versions(
            version1=errata.pkg_version,
            release1=errata.pkg_release,
            version2=package.version,
            release2=package.release,
        )
        < 1
    )


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


class _pHasBranchOptional(Protocol):
    branch: Union[str, None]


class _pHasPkgNameList(Protocol):
    pkg_name: list[str]


class _pHasCveInfo(Protocol):
    cve_info: dict[str, VulnerabilityInfo]


class _pHasCveCpems(Protocol):
    cve_cpems: dict[str, list[CpeMatch]]


class _pHasPackagesCpes(Protocol):
    packages_cpes: dict[str, list[CPE]]


class _pHasPackagesVersions(Protocol):
    packages_versions: list[PackageVersion]


class _pHasPackagesVulnerabilities(Protocol):
    packages_vulnerabilities: list[PackageVulnerability]


class _pGetPackagesCpesCompatible(
    _pHasPackagesCpes, _pHasBranchOptional, _pAPIWorker, Protocol
):
    ...


class _pGetCveInfoCompatible(
    _pHasCveInfo, _pHasCveCpems, _pHasBranchOptional, _pAPIWorker, Protocol
):
    ...


class _pGetLastPackageVersionsCompatible(
    _pHasPackagesVersions,
    _pHasBranchOptional,
    _pAPIWorker,
    Protocol,
):
    ...


class _pGetLastMatchedPackagesVersionsCompatible(
    _pHasCveCpems,
    _pHasPackagesCpes,
    _pHasPackagesVersions,
    _pHasBranchOptional,
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


class _pGetVulnerabilityFixErrataCompatible(
    _pHasPackagesVulnerabilities, _pHasBranchOptional, _pAPIWorker, Protocol
):
    ...


# Mixin
def get_cve_info(cls: _pGetCveInfoCompatible, cve_ids: Iterable[str]) -> None:
    cls.status = False
    # 1. check if CVE info in DB
    tmp_table = make_tmp_table_name("vuiln_ids")

    response = cls.send_sql_request(
        cls.sql.get_vuln_info_by_ids.format(tmp_table=tmp_table),
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
        _ = cls.store_error({"message": f"No data info found in DB for {cve_ids}"})
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
        _ = cls.store_error(
            {"message": f"No CPE matches data info found in DB for {cve_ids}"}
        )
        return None

    cls.cve_cpems = {el[0]: [CpeMatch(*x) for x in el[1]] for el in response}

    cls.status = True


def get_packages_cpes(cls: _pGetPackagesCpesCompatible) -> None:
    cls.status = False

    cpe_branches = tuple({v for v in cls.sql.CPE_BRANCH_MAP.values()})
    if cls.branch is not None:
        cpe_branch = cls.sql.CPE_BRANCH_MAP.get(cls.branch, None)
        if cpe_branch is None:
            _ = cls.store_error(
                {"message": f"No CPE branch mapping found for branch {cls.branch}"}
            )
            return None
        cpe_branches = (cpe_branch,)

    response = cls.send_sql_request(
        cls.sql.get_packages_and_cpes.format(cpe_branches=cpe_branches)
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
    cls: _pGetLastPackageVersionsCompatible, pkg_names: Iterable[tuple[str, Any]]
) -> None:
    cls.status = False

    branches = tuple(cls.sql.CPE_BRANCH_MAP.keys())
    if cls.branch is not None:
        branches = (cls.branch,)

    tmp_table = make_tmp_table_name("pkg_names")

    response = cls.send_sql_request(
        cls.sql.get_packages_versions.format(branches=branches, tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("pkg_name", "String")],
                "data": [{"pkg_name": p[0]} for p in pkg_names],
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


def get_last_matched_packages_versions(
    cls: _pGetLastMatchedPackagesVersionsCompatible,
) -> None:
    cls.status = False
    matched_packages: list[tuple[str, CPE]] = []

    cve_cpe_triplets = {
        (cpem.cpe.vendor, cpem.cpe.product, cpem.cpe.target_sw)
        for cpems in cls.cve_cpems.values()
        for cpem in cpems
    }

    for pkg, cpe in (
        (pkg, cpe) for pkg, cpes in cls.packages_cpes.items() for cpe in cpes
    ):
        if (cpe.vendor, cpe.product, cpe.target_sw) in cve_cpe_triplets:
            matched_packages.append((pkg, cpe))

    # 4. check if last branch (all branches if `branch` not specified) packages are vulnerable
    get_last_packages_versions(cls, matched_packages)


def get_packages_vulnerabilities(cls: _pGetPackagesVulnerabilitiesCompatible) -> None:
    cls.status = False

    for vuln_id, cpems in cls.cve_cpems.items():
        cve_cpe_triplets = {
            (cpem.cpe.vendor, cpem.cpe.product, cpem.cpe.target_sw) for cpem in cpems
        }

        for pkg in cls.packages_versions:
            pkg_cpe_triplets = {
                (cpe.vendor, cpe.product, cpe.target_sw)
                for cpe in cls.packages_cpes[pkg.name]
            }

            if not cve_cpe_triplets.intersection(pkg_cpe_triplets):
                continue

            cls.packages_vulnerabilities.append(
                PackageVulnerability(**pkg._asdict(), vuln_id=vuln_id).match_by_version(
                    (
                        cpem
                        for cpem in cpems
                        if (cpem.cpe.vendor, cpem.cpe.product, cpem.cpe.target_sw)
                        in pkg_cpe_triplets
                    )
                )
            )

    cls.packages_vulnerabilities = sorted(
        cls.packages_vulnerabilities,
        key=lambda x: (x.vuln_id, x.branch, x.vulnerable, x.name, x.version),
    )

    cls.status = True


def get_vulnerability_fix_errata(cls: _pGetVulnerabilityFixErrataCompatible) -> None:
    cls.status = False

    branch_clause = ""
    if cls.branch is not None:
        branch_clause = f"AND pkgset_name = '{cls.branch}'"

    # get Errata where CVE is closed for vulnerable packages and not commited
    # to repository yet if any
    tmp_table = make_tmp_table_name("packages")

    response = cls.send_sql_request(
        cls.sql.get_errata_by_packages.format(
            branch_clause=branch_clause, tmp_table=tmp_table
        ),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("pkg_name", "String")],
                "data": [
                    {"pkg_name": pkg_name}
                    for pkg_name in {p.name for p in cls.packages_vulnerabilities}
                ],
            }
        ],
    )
    if not cls.sql_status:
        return None
    if response:
        erratas = [Errata(*el[1]) for el in response]

        # get last state for tasks in erratas
        task_states: dict[int, str] = {}

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
            task_states = {el[0]: el[1] for el in response}

        # check found erratas for vulnerability fixes
        for pkg in cls.packages_vulnerabilities:
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

    cls.status = True


def get_vulnerablities_from_errata(
    cls: _pGetVulnerabilityFixErrataCompatible, cve_ids: list[str]
) -> None:
    cls.status = False

    # XXX: ignore branch if provided
    branch_clause = ""
    # if cls.branch is not None:
    #     branch_clause = f"AND pkgset_name = '{cls.branch}'"

    # find errata by branch (if set) and CVE ids
    response = cls.send_sql_request(
        cls.sql.get_errata_by_cves.format(branch_clause=branch_clause, cve_ids=cve_ids)
    )
    if not cls.sql_status:
        return None
    if response:
        erratas = [Errata(*el[1]) for el in response]
        print(erratas)

        # get last task states
        # get last state for tasks in erratas
        task_states: dict[int, str] = {}

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
            task_states = {el[0]: el[1] for el in response}

        # build vulnerable packages list from erratas
        for errata in erratas:
            # update task state
            errata.task_state = task_states.get(errata.task_id, errata.task_state)
            # add PackageVulnerability record
            cls.packages_vulnerabilities.append(
                PackageVulnerability(
                    hash=errata.pkg_hash,
                    name=errata.pkg_name,
                    version=errata.pkg_version,
                    release=errata.pkg_release,
                    branch=errata.branch,
                    vuln_id=errata.id,
                    fixed=True,
                    fixed_in=[errata],
                )
            )

        if cls.packages_vulnerabilities:
            cls.status = True
    else:
        _ = cls.store_error({"message": f"No errata records found for {cve_ids}"})
