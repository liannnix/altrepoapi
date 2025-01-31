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
from dataclasses import dataclass
from itertools import groupby
from typing import NamedTuple, Any

from altrepo_api.api.base import APIWorker
from altrepo_api.libs.librpm_functions import check_dependency_overlap
from altrepo_api.utils import make_tmp_table_name
from altrepo_api.api.package.endpoints.misconflict_packages import MisconflictPackages

from ..sql import sql


class BinaryPackageArchs(NamedTuple):
    """
    Architecture and hash of the input binary package.
    """

    arch: str
    pkghash: int


@dataclass
class BinaryPackage:
    """
    Information about the input binary package.
    """

    name: str
    archs: list[BinaryPackageArchs]  # list of binary packages (arch, hash) tuples

    def __init__(self, pkg_info: tuple[str, list[tuple[str, int]]]):
        self.name = pkg_info[0]
        self.archs = [BinaryPackageArchs(*el) for el in pkg_info[1]]


class ConflictPackage(NamedTuple):
    """
    Information about the conflicting package.
    """

    input_package: str
    input_arch: str = ""
    conflict_package: str = ""
    version: str = ""
    release: str = ""
    epoch: int = 0
    dp_name: str = ""
    dp_version: str = ""
    dp_flag: int = 0
    conf_hash: int = 0
    conf_arch: str = ""
    files_with_conflict: list[str] = []
    explicit: bool = False


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
        binary_packages_map: dict[BinaryPackageArchs, ConflictPackage] = {}
        input_archs: dict[str, list[str]] = {}
        for pkg in (BinaryPackage(el[:2]) for el in response):
            input_archs[pkg.name] = []
            for arch_hash in pkg.archs:
                binary_packages_map[arch_hash] = ConflictPackage(
                    input_package=pkg.name, input_arch=arch_hash.arch
                )
                input_archs[pkg.name].append(arch_hash.arch)

        # get information about conflicting packages
        tmp_table = make_tmp_table_name("input_pkg_hshs")
        response = self.send_sql_request(
            self.sql.get_conflicts_pkg_hshs.format(tmp_table=tmp_table, branch=branch),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("pkg_hash", "UInt64"), ("arch", "String")],
                    "data": [
                        {"pkg_hash": el.pkghash, "arch": el.arch}
                        for el in binary_packages_map.keys()
                    ],
                },
            ],
        )
        if not self.sql_status:
            return self.error

        if response:
            for el in response:
                input_hash, cp = el[0], ConflictPackage("", *el[1:])
                if check_dependency_overlap(
                    provide_dep_name=cp.conflict_package,
                    provide_dep_version=f"{cp.version}-{cp.release}",
                    provide_dep_flags=0,
                    require_dep_name=cp.dp_name,
                    require_dep_version=cp.dp_version,
                    require_dep_flags=cp.dp_flag,
                ):
                    map_key = BinaryPackageArchs(arch=cp.input_arch, pkghash=input_hash)
                    binary_packages_map[map_key] = cp._replace(
                        input_package=binary_packages_map[map_key].input_package
                    )

        conflict_hashes = set()
        for input_arch_hash, value in binary_packages_map.items():
            if value.conf_hash:
                conflict_hashes.add(
                    (input_arch_hash.pkghash, value.conf_hash, input_arch_hash.arch)
                )

        # name for temporary table with hashes of input and conflicting package
        tmp_table = make_tmp_table_name("conflict_hashes")
        # get information about conflicting files
        response = self.send_sql_request(
            self.sql.get_conflict_files.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [
                        ("input_hash", "UInt64"),
                        ("conf_hash", "UInt64"),
                        ("arch", "String"),
                    ],
                    "data": [
                        {"input_hash": hsh[0], "conf_hash": hsh[1], "arch": hsh[2]}
                        for hsh in conflict_hashes
                    ],
                },
            ],
        )
        if not self.sql_status:
            return

        if response:
            for el in response:
                map_key = BinaryPackageArchs(arch=el[1], pkghash=el[0])
                binary_packages_map[map_key] = binary_packages_map[map_key]._replace(
                    files_with_conflict=sorted(el[2]), explicit=True
                )

        def keyfunc(item: ConflictPackage):
            return (
                item.input_package,
                item.conflict_package,
                item.files_with_conflict,
            )

        resolved_conflicts: list[dict[str, Any]] = []

        # sort conflicting packages by input package, conflicting package and files
        conflict_packages = sorted(binary_packages_map.values(), key=keyfunc)

        # group conflicting packages by input package, conflicting package and files
        for key, group in groupby(conflict_packages, key=keyfunc):
            group = list(group)

            # convert to list of dictionaries that compatible
            # with MisconflictPackages.find_conflicts() result
            conflict = group[0]._asdict()
            if conflict["explicit"]:
                conflict["input_archs"] = set()
                conflict["archs"] = set()
                # group conflicting packages by architectures and list of files
                for el in group:
                    conflict["input_archs"].add(el.input_arch)
                    conflict["archs"].add(el.conf_arch)
                resolved_conflicts.append(conflict)

        # get misconflict
        mp = MisconflictPackages(
            self.conn,
            tuple(),
            branch.lower(),
            [],
        )
        mp.find_conflicts(tuple([el.pkghash for el in binary_packages_map.keys()]))

        if mp.status:
            mp.result += resolved_conflicts
            if mp.result:
                for el in mp.result:
                    # add input package architectures in the
                    # MisconflictPackages.find_conflicts() result
                    if not el.get("explicit"):
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
