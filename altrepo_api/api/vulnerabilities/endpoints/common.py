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
from typing import Any, Iterable, Literal, NamedTuple

from altrepo_api.libs.librpm_functions import compare_versions, version_less_or_equal


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
    refs: list[str]

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
