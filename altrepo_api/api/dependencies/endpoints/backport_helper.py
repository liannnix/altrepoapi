# ALTRepo API
# Copyright (C) 2023  BaseALT Ltd

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

from re import match
from typing import NamedTuple, Iterable, Literal
from collections import defaultdict

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.libs.librpm_functions import check_dependency_overlap

from ..sql import sql


# TODO: fill the table
BACKPORT_TABLE: dict[str, list[str]] = {
    "sisyphus": ["p10"],
    "p10": ["p9", "c9f2"],
    "p9": ["p8"],
    "p8": ["p7"],
    "p7": [],
    "c9f2": ["c9f1"],
    "c9f1": [],
    "c8.1": ["c8"],
    "c7.1": ["c7"],
    "sisyphus_e2k": ["p10_e2k"],
    "p10_e2k": ["p9_e2k"],
    "p9_e2k": [],
}


def backport_possible(source_branch: str, destination_branch: str) -> bool:
    return destination_branch in BACKPORT_TABLE[source_branch]


class Package(NamedTuple):
    srpm: str
    name: str
    epoch: int
    version: str
    release: str
    arch: str


class Dependency(NamedTuple):
    srpm: str
    name: str
    epoch: int
    version: str
    release: str
    arch: str
    dp_type: str
    dp_name: str
    dp_flag: int
    dp_version: str


class BackportHelper(APIWorker):
    """Find packages required to backport too."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def _get_dependencies(
        self, branch: str, dpnames: Iterable[str], dptype: Literal["provide", "require"]
    ) -> set[Dependency]:
        _tmp_table = "tmp_names"
        response = self.send_sql_request(
            self.sql.get_dependencies.format(
                branch=branch,
                archs=tuple(self.archs),
                dptype=dptype,
                tmp_table=_tmp_table,
            ),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [("name", "String")],
                    "data": [{"name": name} for name in dpnames],
                },
            ],
        )
        return {Dependency(*r) for r in response}

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if not backport_possible(self.args["from_branch"], self.args["into_branch"]):
            self.validation_results.append("backport is not possible")

        if (set(self.args["archs"]) - set(lut.known_archs)):
            self.validation_results.append("unknown architecture(-s)")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        def linked_arches(requirement: Dependency, providement: Dependency) -> bool:
            return requirement.arch in ("src", "noarch") or requirement.arch in (
                providement.arch,
                "noarch",
            )

        def find_unmet_dependencies(
            requirements: set[Dependency], providements: set[Dependency]
        ) -> set[Dependency]:
            resolved = set()
            for req in requirements:
                for prov in providements:
                    if linked_arches(req, prov):
                        if check_dependency_overlap(
                            prov.dp_name,
                            prov.dp_version,
                            prov.dp_flag,
                            req.dp_name,
                            req.dp_version,
                            req.dp_flag,
                        ):
                            resolved.add(req)

                # All 'rpmlib' requires are always provided by rpm.
                if match(r"rpmlib(.*)", req.dp_name):
                    resolved.add(req)
                # All files requires don't have providers (at least in the database).
                if match(r"(\/.*)+", req.dp_name):
                    resolved.add(req)
            return requirements - resolved

        from_branch = self.args["from_branch"]
        into_branch = self.args["into_branch"]
        packages_names = self.args["packages_names"]
        dp_type = self.args["dp_type"]

        # Use virtual "src" architecture to resolve "source" dependency type.
        self.archs = ["noarch", "src"]
        if self.args["archs"]:
            self.archs += self.args["archs"]

        depth = 0
        dependencies_names = set(packages_names)
        memory = set()

        backport_list: list[tuple[int, set[Package]]] = []

        while dependencies_names:
            dependencies_names = dependencies_names.difference(memory)

            requires = self._get_dependencies(
                from_branch, dependencies_names,  "require"
            )
            provides = self._get_dependencies(
                into_branch, {d.dp_name for d in requires}, "provide"
            )

            unmet_dependencies = find_unmet_dependencies(requires, provides)

            if dp_type == "binary":
                unmet_dependencies = set(
                    filter(lambda d: d.arch != "src", unmet_dependencies)
                )
            if dp_type == "source":
                unmet_dependencies = set(
                    filter(lambda d: d.arch == "src", unmet_dependencies)
                )

            memory = memory.union(dependencies_names)

            dependencies_names = {d.dp_name for d in unmet_dependencies}

            backport_list.append((depth, {Package(*d[:6]) for d in unmet_dependencies}))

            depth += 1

        # deduplication for O(n) + removing packages with 'src' arch
        flattened = {
            package: depth
            for depth, level in backport_list
            for package in level
            if package.arch != "src" and depth != 0
        }
        dedup = [(i + 1, k) for i, (k, _) in enumerate(flattened.items())]

        count = len(dedup)
        maxdepth = max([depth for depth, _ in dedup]) if dedup else 0

        # back to levels
        backports = defaultdict(list)
        for depth, package in dedup:
            backports[depth].append(package._asdict())

        res = {
            "request_args": self.args,
            "count": count,
            "maxdepth": maxdepth,
            "dependencies": sorted(
                [
                    {
                        "depth": depth,
                        "packages": sorted(level, key=lambda p: p["srpm"]),
                    }
                    for depth, level in backports.items()
                ],
                key=lambda e: e["depth"],
                reverse=True,
            ),
        }
        return res, 200
