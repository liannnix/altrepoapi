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
from typing import Any, Iterable, Iterator, NamedTuple, Optional, Union

from altrepodb_libs import (
    PackageCveMatch,
    VersionCompareResult,
    mmhash64,
    evrdt_compare,
    version_compare,
    version_less_or_equal,
)

from altrepo_api.api.misc import lut
from altrepo_api.api.vulnerabilities.endpoints.common import CPE, CpeMatchVersions

from ..tools.base import Errata, PncRecord


CVE_ID_PREFIX = "CVE-"


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


def is_version_release_eq(*, v1: str, r1: str, v2: str, r2: str) -> bool:
    return (
        evrdt_compare(version1=v1, release1=r1, version2=v2, release2=r2)
        == VersionCompareResult.EQUAL
    )


def branch_inheritance_list(b: str) -> dict[str, int]:
    if b not in lut.branch_inheritance:
        return {lut.branch_inheritance_root: 0}

    if b == lut.branch_inheritance_root:
        return {b: 0}

    return {x: i for i, x in enumerate([b] + lut.branch_inheritance[b])}


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


def is_cve_in_errata_references(cve_id: str, errata: Errata) -> bool:
    return cve_id in (r.link for r in errata.references)


def cves_from_vulns(vulns: Iterable[str]) -> set[str]:
    return {v for v in vulns if v.startswith(CVE_ID_PREFIX)}


def errata_cves_diff(cves: Iterable[str], errata: Errata) -> Optional[set[str]]:
    res = set()
    refs = {e.link for e in errata.references}
    for cve in cves:
        if cve not in refs:
            res.add(cve)
    return res if res else None


def group_tasks_by_branch(
    tasks: dict[str, list[PackageTask]]
) -> dict[str, list[PackageTask]]:
    res: dict[str, list[PackageTask]] = {}
    for task in (t for tt in tasks.values() for t in tt):
        res.setdefault(task.branch, []).append(task)
    return res


def group_tasks_by_branch_and_name(
    tasks: dict[str, list[PackageTask]]
) -> dict[str, dict[str, list[PackageTask]]]:
    res: dict[str, dict[str, list[PackageTask]]] = {}
    for task in (t for tt in tasks.values() for t in tt):
        res.setdefault(task.branch, {}).setdefault(task.name, []).append(task)
    return res


def is_package_vulnerable(pkg: PackageTask, cpm: CpeMatchVersions) -> bool:
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


def is_cpm_version_upper_boung_gt(
    new_cmv: CpeMatchVersions, prev_cmv: CpeMatchVersions
) -> bool:
    cmp = version_compare(version1=new_cmv.version_end, version2=prev_cmv.version_end)
    if cmp == VersionCompareResult.GREATER_THAN:
        # if new version range upper bound is greater that previous use it no matter
        # what bound flags are
        return True

    if cmp == VersionCompareResult.EQUAL:
        # bound flags are equial -> only version comparison is mater
        if new_cmv.version_end_excluded == prev_cmv.version_end_excluded:
            return False
        # new version bound exclusion flag is not set and old is set
        if not new_cmv.version_end_excluded and prev_cmv.version_end_excluded:
            return True
        # new version bound exclusion flag is set and old is not set
        pass

    # new version is less or equal with version bound exclusion flags [new, prev] == [True, False]
    return False


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
