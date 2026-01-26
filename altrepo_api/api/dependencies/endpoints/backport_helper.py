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

from collections import defaultdict
from re import match
from typing import NamedTuple, Iterable, Literal

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.api.task.endpoints.task_repo import LastRepoStateFromTask
from altrepo_api.libs.librpm_functions import check_dependency_overlap

from ..sql import sql


# TODO: fill the table
BACKPORT_TABLE: dict[str, list[str]] = {
    "sisyphus": ["p11"],
    "p11": ["p10"],
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
        self,
        branch_deps_table_name: str,
        dpnames: Iterable[str],
        dptype: Literal["provide", "require"],
    ) -> set[Dependency]:
        _tmp_table = "tmp_names"
        response = self.send_sql_request(
            self.sql.get_dependencies.format(
                branch_deps_table_name=branch_deps_table_name,
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
            self.validation_results.append(
                f'Branch {self.args["from_branch"]} not inherited from  {self.args["into_branch"]}'
            )

        excessive_archs = set()
        if self.args["archs"] is not None:
            excessive_archs = set(self.args["archs"]) - set(lut.known_archs)
        if excessive_archs:
            self.validation_results.append(
                f"unknown architecture(-s): {excessive_archs}"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        def find_unmet_dependencies(
            requirements: set[Dependency],
            providements_index: dict[str, list[Dependency]],
        ) -> set[Dependency]:
            resolved = set()
            for req in requirements:
                provs = providements_index.get(req.dp_name, [])
                for prov in provs:
                    if req.arch in ("src", "noarch", prov.arch):
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

        FROM_BRANCH_TABLE = "DepsFromBranch"
        INTO_BRANCH_TABLE = "DepsIntoBranch"

        def fill_tmp_table(table_name: str, branch: str, template: str, **kwargs):
            self.send_sql_request(
                self.sql.create_tmp_table.format(
                    tmp_table=table_name,
                    columns=template.format(branch=branch),
                ),
                **kwargs,
            )

        for branch, table in (
            (from_branch, FROM_BRANCH_TABLE),
            (into_branch, INTO_BRANCH_TABLE),
        ):
            if branch in lut.taskless_branches:
                fill_tmp_table(table, branch, self.sql.taskless_template)
                if not self.sql_status:
                    return self.error
                continue

            ls = LastRepoStateFromTask(self.conn, branch)
            ls.build_repo_state()
            if not ls.status:
                return ls.error

            kwargs = {}
            hashes = ls.task_repo_pkgs
            if not hashes:
                _template = self.sql.taskless_template
            else:
                _ext_table = "ext_hashes"
                _template = self.sql.task_template.format(ext_table=_ext_table)
                kwargs = {
                    "external_tables": [
                        {
                            "name": _ext_table,
                            "structure": [("pkg_hash", "UInt64")],
                            "data": [{"pkg_hash": pkg_hash} for pkg_hash in hashes],
                        },
                    ]
                }

            fill_tmp_table(table, branch, _template, **kwargs)
            if not self.sql_status:
                return self.error

        # Use virtual "src" architecture to resolve "source" dependency type.
        self.archs = ["noarch", "src"]
        if self.args["archs"]:
            self.archs += self.args["archs"]
        else:
            # if there are 'noarch' and 'src' only then add default arch ('x86_64')
            self.archs += ["x86_64"]

        depth = 0
        dependencies_names = set(packages_names)
        memory = set()

        backport_list: list[tuple[int, set[Package]]] = []

        while dependencies_names:
            dependencies_names = dependencies_names.difference(memory)

            requires = self._get_dependencies(
                FROM_BRANCH_TABLE, dependencies_names, "require"
            )

            provides_index = defaultdict(list)
            for prov in self._get_dependencies(
                INTO_BRANCH_TABLE,
                {req.dp_name for req in requires},
                "provide",
            ):
                provides_index[prov.dp_name].append(prov)

            unmet_dependencies = find_unmet_dependencies(requires, provides_index)

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

            backport_list.append(
                (
                    depth,
                    {Package(*d[:6]) for d in unmet_dependencies | requires},
                )
            )

            depth += 1

        max_depth = 0
        uniq_packages: dict[Package, int] = {}

        for depth, package in (
            (lvl, pkg)
            for lvl, pkgs in backport_list
            for pkg in pkgs
            if pkg.arch != "src"
        ):
            if depth > uniq_packages.get(package, 0):
                uniq_packages[package] = depth
            if depth > max_depth:
                max_depth = depth

        # back to levels
        levels = defaultdict(list)
        for package, depth in uniq_packages.items():
            levels[depth].append(package._asdict())

        dependencies = [
            {
                "depth": depth,
                "packages": sorted(packages, key=lambda p: (p["srpm"], p["name"])),
            }
            for depth, packages in enumerate(levels.values(), start=1)
        ]

        res = {
            "request_args": self.args,
            "count": sum(len(p["packages"]) for p in dependencies),
            "maxdepth": len(dependencies),
            "dependencies": sorted(
                dependencies, key=lambda level: level["depth"], reverse=True
            ),
        }
        return res, 200
