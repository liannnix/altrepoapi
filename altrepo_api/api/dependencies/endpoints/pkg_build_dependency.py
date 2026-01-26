# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

from typing import Any
from dataclasses import dataclass, field, asdict

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.libs.librpm_functions import check_dependency_overlap
from altrepo_api.utils import dp_flags_decode

from ..sql import sql


@dataclass
class DependencyInfo:
    pkghash: str
    name: str
    arch: str
    dp_name: str
    dp_version: str
    dp_flag: int
    dp_flag_decoded: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.dp_flag_decoded = dp_flags_decode(self.dp_flag, lut.rpmsense_flags)


@dataclass
class PackageDepends:
    requires: DependencyInfo
    provides: DependencyInfo
    is_valid: bool = False

    def __init__(self, data: tuple[Any]):
        self.requires = DependencyInfo(*data[:6])
        self.provides = DependencyInfo(*data[6:])
        self.is_valid = check_dependency_overlap(
            provide_dep_name=self.provides.dp_name,
            provide_dep_version=self.provides.dp_version,
            provide_dep_flags=self.provides.dp_flag,
            require_dep_name=self.requires.dp_name,
            require_dep_version=self.requires.dp_version,
            require_dep_flags=self.requires.dp_flag,
        )


@dataclass
class Dependencies:
    pkghash: str
    name: str
    buildtime: str
    branch: str
    acl: list[str]
    depends: list[PackageDepends]

    def __init__(self, data: tuple[str, str, str, str, list[tuple]]):
        self.pkghash, self.name, self.buildtime, self.branch, dependencies = data
        self.acl = []
        self.depends = []
        for dep in dependencies:
            dependency = PackageDepends(dep)
            if dependency.is_valid:
                self.depends.append(dependency)

    def asdict(self) -> dict[str, Any]:
        res = asdict(self)
        return res


class PackageBuildDependency(APIWorker):
    """Retrieves packages build dependencies."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        pkg_name = self.args["name"]
        branch = self.args["branch"]
        dptype = self.args["dp_type"]
        depends_type_to_sql = {"source": (1,), "binary": (0,), "both": (1, 0)}
        sourcef = depends_type_to_sql[dptype]

        arch = (
            lut.branch_wds_default_archs.get(branch)
            or lut.branch_wds_default_archs["default"]
        )

        response = self.send_sql_request(
            self.sql.get_what_depends_src.format(
                pkg_name=pkg_name,
                branch=branch,
                archs=arch,
                src_archs=arch + ["srpm"],
                sfilter=sourcef,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args,
                }
            )

        dependencies = [Dependencies(el) for el in response]

        # get package acl
        _src_pkgs_tmp_table = "src_pkgs_tmp_table"
        response = self.send_sql_request(
            self.sql.get_acl.format(tmp_table=_src_pkgs_tmp_table, branch=branch),
            external_tables=[
                {
                    "name": _src_pkgs_tmp_table,
                    "structure": [
                        ("pkgname", "String"),
                    ],
                    "data": [{"pkgname": dep.name} for dep in dependencies],
                }
            ],
        )
        if not self.sql_status:
            return self.error

        acl_dict = {acl[0]: acl[1][0] for acl in response}
        update_deps = []
        for dep in dependencies:
            if dep.name != pkg_name and dep.depends != []:
                dep.acl = acl_dict.get(dep.name, [])
                update_deps.append(dep.asdict())

        res = {
            "request_args": self.args,
            "length": len(update_deps),
            "dependencies": update_deps,
        }
        return res, 200
