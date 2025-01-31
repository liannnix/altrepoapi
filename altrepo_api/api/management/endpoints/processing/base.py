# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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

from datetime import datetime
from functools import cmp_to_key
from typing import Any, Iterator, NamedTuple, Optional, Union

from altrepodb_libs import (
    PackageCveMatch,
    VersionCompareResult,
    mmhash64,
    evrdt_compare,
    version_less_or_equal,
)

from altrepo_api.api.misc import lut
from altrepo_api.api.vulnerabilities.endpoints.common import CPE, CpeMatchVersions

from ..tools.base import Errata, PncRecord


class ErrataProcessingError(Exception):
    pass


class ErrataBuilderError(ErrataProcessingError):
    pass


class ErrataHandlerError(ErrataProcessingError):
    pass


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


class ChangelogErrataPoint(NamedTuple):
    task: PackageTask
    evr: str
    cve_ids: tuple[str, ...]


class CpeRecord(NamedTuple):
    cpe: CPE
    state: str
    project_name: str

    def asdict(self) -> dict[str, str]:
        return {
            "cpe": str(self.cpe),
            "state": self.state,
            "project_name": self.project_name,
        }


class CpeRaw(NamedTuple):
    state: str
    name: str
    repology_name: str
    repology_branch: str
    cpe: str


def cpe_record2pnc_record(cpe: CpeRecord) -> PncRecord:
    return PncRecord(
        pkg_name=cpe.project_name,
        pnc_state=cpe.state,
        pnc_result=str(cpe.cpe),
        pnc_type="cpe",
        pnc_source="manage",
    )


def compare_pnc_records(a: PncRecord, b: PncRecord, *, include_state: bool) -> bool:
    if include_state:
        return (a.pkg_name, a.pnc_state, a.pnc_result, a.pnc_type) == (
            b.pkg_name,
            b.pnc_state,
            b.pnc_result,
            b.pnc_type,
        )
    else:
        return (a.pkg_name, a.pnc_result, a.pnc_type) == (
            b.pkg_name,
            b.pnc_result,
            b.pnc_type,
        )


def version_release_compare(
    *, v1: str, r1: str, v2: str, r2: str
) -> VersionCompareResult:
    return evrdt_compare(version1=v1, release1=r1, version2=v2, release2=r2)


def version_release_less_or_equal(e: Errata, p: PackageVersion) -> bool:
    return version_release_compare(
        v1=e.pkg_version, r1=e.pkg_release, v2=p.version, r2=p.release
    ) in (VersionCompareResult.EQUAL, VersionCompareResult.LESS_THAN)


def branch_inheritance_list(b: str) -> dict[str, int]:
    if b not in lut.branch_inheritance:
        return {lut.branch_inheritance_root: 0}

    if b == lut.branch_inheritance_root:
        return {b: 0}

    return {x: i for i, x in enumerate([b] + lut.branch_inheritance[b])}


def collect_erratas(branch: str, erratas: list[Errata]) -> list[Errata]:
    """Collect existing erratas by branch and sorts it descending by package'
    version and release in accordance to branch inheritance order.
    """

    inheritance_list = branch_inheritance_list(branch)

    def compare_erratas(a: Errata, b: Errata) -> int:
        if a.pkg_name != b.pkg_name:
            raise ValueError("Failed to compare Erratas for different packages")

        vr_cmp = int(
            version_release_compare(
                v1=a.pkg_version, r1=a.pkg_release, v2=b.pkg_version, r2=b.pkg_release
            )
        )

        if vr_cmp != 0:
            return vr_cmp

        a_branch_idx = inheritance_list[a.pkgset_name]
        b_branch_idx = inheritance_list[b.pkgset_name]

        if a_branch_idx < b_branch_idx:
            return 1
        elif a_branch_idx > b_branch_idx:
            return -1
        return 0

    return sorted(
        [e for e in erratas if e.pkgset_name in inheritance_list],
        key=cmp_to_key(compare_erratas),
        reverse=True,
    )


def find_errata_by_package_task(
    t: PackageTask, erratas: list[Errata]
) -> Optional[Errata]:
    """Find exact Errata from list matching by by task_id, package name,
    version and release.
    """

    for e in erratas:
        if (e.task_id, e.pkg_name, e.pkg_version, e.pkg_release) == (
            t.task_id,
            t.name,
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


def package_is_vulnerable(pkg: PackageTask, cpm: CpeMatchVersions) -> bool:
    # XXX: always match the package for CPE with version unspecified
    if (
        cpm.version_start == ""
        and cpm.version_end == ""
        and not cpm.version_start_excluded
        and not cpm.version_end_excluded
    ):
        return True

    return version_less_or_equal(
        version1=pkg.version,
        version2=cpm.version_end,
        strictly_less=cpm.version_end_excluded,
    ) and version_less_or_equal(
        version1=cpm.version_start,
        version2=pkg.version,
        strictly_less=cpm.version_start_excluded,
    )


def dedup_pcms(pcms: list[PackageCveMatch]) -> list[PackageCveMatch]:
    key_hashes = set()
    res = []
    for pcm in pcms:
        key_hash = mmhash64(
            pcm.pkg_hash,
            pcm.pkg_cpe_hash,
            pcm.vuln_hash,
            pcm.cpm_cpe_hash,
            pcm.cpm_version_hash,
        )
        if key_hash not in key_hashes:
            res.append(pcm)
            key_hashes.add(key_hash)
    return res


def uniq_pcm_records(
    pcms: list[PackageCveMatch], vulnerable_only: bool
) -> list[dict[str, Any]]:
    """Collects unique packages' CVE matches records in sorted
    serialisable representation."""

    class PCM(NamedTuple):
        pkg_hash: int
        pkg_name: str
        pkg_cpe: str
        vuln_id: str
        is_vulnerable: bool

        def asdict(self) -> dict[str, Any]:
            return {
                "pkg_hash": str(self.pkg_hash),
                "pkg_name": self.pkg_name,
                "pkg_cpe": self.pkg_cpe,
                "vuln_id": self.vuln_id,
                "is_vulnerable": self.is_vulnerable,
            }

    def predicate_is_vulnerable(pcm: PCM) -> bool:
        return pcm.is_vulnerable

    def predicate_dummy(pcm: PCM) -> bool:
        return True

    predicate_fx = predicate_is_vulnerable if vulnerable_only else predicate_dummy

    def pcm_gen() -> Iterator[PCM]:
        for pcm in pcms:
            yield PCM(
                pcm.pkg_hash, pcm.pkg_name, pcm.pkg_cpe, pcm.vuln_id, pcm.is_vulnerable
            )

    def sorting_order_key(pcm: PCM) -> tuple[Any, ...]:
        return (not pcm.is_vulnerable, pcm.vuln_id, pcm.pkg_name, pcm.pkg_hash)

    return list(
        x.asdict()
        for x in sorted(
            {pcm for pcm in pcm_gen() if predicate_fx(pcm)}, key=sorting_order_key
        )
    )
