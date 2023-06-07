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

from typing import Any, NamedTuple

from altrepo_api.api.base import APIWorker
from altrepo_api.libs.librpm_functions import check_dependency_overlap
from altrepo_api.utils import make_tmp_table_name
from altrepo_api.api.package.endpoints.misconflict_packages import MisconflictPackages

from ..sql import sql


class PackageMisconflict(APIWorker):
    """
    Retrieves binary packages file conflicts by source package.
    """

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        branch = self.args["branch"]

        bin_pkg_clause = "AND pkg_name NOT LIKE '%-debuginfo'"
        # get hashes of binary packages
        response = self.send_sql_request(
            self.sql.get_binary_pkgs_from_last_pkgs.format(
                pkghash=self.pkghash, branch=branch, bin_pkg_clause=bin_pkg_clause
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No binary packages data found in database",
                    "args": self.args,
                }
            )
        binary_packages_map: dict[int, dict[str, Any]] = {}
        input_archs: dict[str, list[str]] = {}

        class BinaryPackage(NamedTuple):
            name: str
            archs: list[tuple[str, int]]  # list of binary packages (arch, hash) tuples

        for pkg in (BinaryPackage(*el[:2]) for el in response):
            input_archs[pkg.name] = []
            for el in pkg.archs:
                binary_packages_map[el[1]] = {"input_package": pkg.name}
                input_archs[pkg.name].append(el[0])

        # get information about conflicting packages
        tmp_table = make_tmp_table_name("input_pkg_hshs")
        response = self.send_sql_request(
            self.sql.get_conflicts_pkg_hshs.format(tmp_table=tmp_table, branch=branch),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("pkg_hash", "UInt64"),],
                    "data": [
                        {"pkg_hash": el}
                        for el in binary_packages_map.keys()
                    ],
                },
            ],
        )
        if not self.sql_status:
            return self.error

        if response:
            class ConflictPackage(NamedTuple):
                conflict_package: str
                version: str
                release: str
                epoch: int
                dp_name: str
                dp_version: str
                dp_flag: int
                conf_hshs: list[int]
                archs: list[str]

            for el in response:
                cp = ConflictPackage(*el[1:])
                if el[0] in binary_packages_map.keys() and check_dependency_overlap(
                    provide_dep_name=cp.conflict_package,
                    provide_dep_version=f"{cp.version}-{cp.release}",
                    provide_dep_flags=0,
                    require_dep_name=cp.dp_name,
                    require_dep_version=cp.dp_version,
                    require_dep_flags=cp.dp_flag,
                ):
                    binary_packages_map[el[0]].update(cp._asdict())

        conflict_hashes = set()
        for input_hash, value in binary_packages_map.items():
            if value.get("conf_hshs"):
                for conf_hash in value.get("conf_hshs"):
                    conflict_hashes.add((input_hash, conf_hash))

        # name for temporary table with hashes of input and conflicting package
        tmp_table = make_tmp_table_name("conflict_hashes")
        # get information about conflicting files
        response = self.send_sql_request(
            self.sql.get_conflict_files.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("input_hash", "UInt64"), ("conf_hash", "UInt64")],
                    "data": [
                        {"input_hash": hsh[0], "conf_hash": hsh[1]}
                        for hsh in conflict_hashes
                    ],
                },
            ],
        )
        if not self.sql_status:
            return

        if response:
            for el in response:
                binary_packages_map[el[0]]["files_with_conflict"] = el[1]
                binary_packages_map[el[0]]["explicit"] = True

        resolved_conflicts = []
        for el in binary_packages_map.values():
            if el.get("explicit") and el not in resolved_conflicts:
                resolved_conflicts.append(el)

        # get misconflict
        mp = MisconflictPackages(
            self.conn,
            tuple(),
            branch.lower(),
            [],
        )
        mp.find_conflicts(tuple(binary_packages_map.keys()))

        if mp.status:
            mp.result += resolved_conflicts
            if mp.result:
                for el in mp.result:
                    el["input_archs"] = input_archs.get(el["input_package"], [])
                # result processing
                res = {
                    "request_args": self.args,
                    "length": len(mp.result),
                    "conflicts": mp.result,
                }
                return res, 200
            else:
                return self.store_error(
                    {
                        "message": "No misconflict packages found in database",
                        "args": self.args,
                    }
                )
        else:
            return mp.error
