# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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

import ctypes
import string
import random

from dataclasses import dataclass
from collections import namedtuple
from typing import Iterable, Literal, NamedTuple

from altrepo_api.api.base import ConnectionProto
from altrepo_api.utils import get_logger

from .exceptions import SqlRequestError

USE_SHADOW_TABLES = True

LIBRPM_SO = "librpm.so"
RPMSENSE_MASK = 0x0F
RPMSENSE_EQUAL = 0x08

logger = get_logger(__name__)

# import librpm library
librpm = ctypes.CDLL(LIBRPM_SO)

rpmRangesOverlap = librpm.rpmRangesOverlap
rpmRangesOverlap.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_uint32,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_uint32,
    ctypes.c_int,
]
rpmRangesOverlap.restype = ctypes.c_int

LIBRPM_NOPROMOTE = ctypes.c_int.in_dll(librpm, "_rpmds_nopromote")


def _make_table_name(prefix: str, length: int = 5) -> str:
    return (
        prefix
        + "_"
        + "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
    )


class Dependency(NamedTuple):
    name: bytes
    evr: bytes
    flags: int


def make_dependency_tuple(name: str, evr: str, flags: int) -> Dependency:
    return Dependency(
        name=name.encode("utf-8"),
        evr=evr.encode("utf-8"),
        flags=(RPMSENSE_MASK & flags),
    )


def checkDependencyOverlap(provide_dep: Dependency, require_dep: Dependency) -> bool:
    """Check dependencies overlapping using librpm `rpmRangesOverlap` function."""
    # set flags for `provides` dependency to RPMSENSE_EQUAL as apt-rpm does
    _provide_dep = Dependency(*provide_dep)._replace(flags=RPMSENSE_EQUAL)
    return bool(rpmRangesOverlap(*_provide_dep, *require_dep, LIBRPM_NOPROMOTE))


@dataclass(frozen=True)
class PackageDependenciesSQL:
    create_tmp_table = """
CREATE TEMPORARY TABLE {tmp_table} (hsh UInt64)
"""

    select_from_tmp_table = """
(SELECT hsh FROM {tmp_table})
"""

    drop_tmp_table = """
DROP TABLE IF EXISTS {tmp_table}
"""

    insert_to_tmp_table = """
INSERT INTO {tmp_tbl} (hsh) VALUES
"""

    create_shadow_last_depends = """
CREATE TEMPORARY TABLE last_depends
(
    pkg_hash UInt64,
    dp_name String,
    dp_version String,
    dp_flag UInt32,
    dp_type Enum8('require' = 1, 'conflict' = 2, 'obsolete' = 3, 'provide' = 4),
    pkg_sourcepackage UInt8,
    pkg_arch String,
    pkgset_name String
)
"""

    fill_shadow_last_depends = """
INSERT INTO last_depends
WITH
BranchPkgHashes AS (
    SELECT pkg_hash
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
)
SELECT
    Depends.*,
    pkg_sourcepackage,
    pkg_arch,
    '{branch}' AS pkgset_name
FROM Depends
INNER JOIN
(
    SELECT
        pkg_hash,
        pkg_sourcepackage,
        pkg_arch
    FROM Packages
    WHERE pkg_hash IN (SELECT * FROM BranchPkgHashes)
) AS PkgSet USING (pkg_hash)
WHERE dp_type IN ('require', 'provide')
    AND pkg_hash IN (SELECT * FROM BranchPkgHashes)
"""

    drop_shadow_last_depends = """
DROP TEMPORARY TABLE last_depends
"""

    get_packages_by_requires = """
WITH reqDeps AS (
    SELECT
        pkg_hash,
        dp_name,
        dp_version,
        dp_flag
    FROM last_depends
    WHERE dp_name NOT LIKE 'rpmlib%'
        AND dp_type = 'require'
        AND pkg_hash IN (SELECT hsh FROM {tmp_table})
)
SELECT DISTINCT
    pkg_hash AS hash,
    groupUniqArray(tuple(dp_name, dp_version, dp_flag)) AS deps,
    'require' AS type
FROM reqDeps
GROUP BY hash
UNION ALL
SELECT DISTINCT
    pkg_hash AS hash,
    groupUniqArray(tuple(dp_name, dp_version, dp_flag)) AS deps,
    'provide' AS type
FROM last_depends
WHERE dp_name IN (SELECT DISTINCT dp_name FROM reqDeps)
    AND dp_type = 'provide'
    AND pkg_sourcepackage = 0
    AND pkg_arch IN {archs}
    AND pkgset_name = '{branch}'
GROUP BY hash
""" if USE_SHADOW_TABLES else """
    WITH reqDeps AS (
        SELECT
            pkg_hash,
            dp_name,
            dp_version,
            dp_flag
        FROM Depends
        WHERE dp_name NOT LIKE 'rpmlib%'
            AND dp_type = 'require'
            AND pkg_hash IN (SELECT hsh FROM {tmp_table})
    ),
    binPkgHshsByBranchAndArch AS (
        SELECT pkg_hash
        FROM Packages
        WHERE pkg_hash IN (
            SELECT pkg_hash
            FROM static_last_packages
            WHERE pkgset_name = '{branch}'
                AND pkg_sourcepackage = 0
        )
            AND pkg_arch IN {archs}
    )
    SELECT DISTINCT
        pkg_hash AS hash,
        groupUniqArray(tuple(dp_name, dp_version, dp_flag)) AS deps,
        'require' AS type
    FROM reqDeps
    GROUP BY hash
    UNION ALL
    SELECT DISTINCT
        pkg_hash AS hash,
        groupUniqArray(tuple(dp_name, dp_version, dp_flag)) AS deps,
        'provide' AS type
    FROM Depends
    WHERE dp_name IN (SELECT DISTINCT dp_name FROM reqDeps)
        AND dp_type = 'provide'
        AND pkg_hash IN (SELECT pkg_hash FROM binPkgHshsByBranchAndArch)
    GROUP BY hash
"""

    get_packages_by_provides = """
"""

    get_meta_by_hshs = """
SELECT
    groupUniqArray(pkg_hash),
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_epoch,
    groupUniqArray(pkg_arch)
FROM Packages
WHERE pkg_hash IN
(
    SELECT hsh
    FROM {tmp_table}
)
GROUP BY
(
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_epoch
)
"""


class PackageDependencies:
    """
    Retrieves source packages dependencies from database.

    Result list contains binary packages that providing required dependencies.
    Dependency tree resolved recursively until all related packages are collected.
    """

    def __init__(
        self,
        connection: ConnectionProto,
        source_packages_hashes: Iterable[int],
        branch: str,
        archs: list[str],
        debug_sql: bool = False,
    ):
        self.conn = connection
        self.sql = PackageDependenciesSQL()
        self.source_packages_hashes = source_packages_hashes
        self.archs = archs
        self.branch = branch
        self.dependencies_dict: dict[int, set[int]] = {}
        self.deps_tree_dict: dict[int, set[int]] = {}
        self.error = ""
        self._debug = debug_sql
        self._tmp_table = "tmp_pkg_hshs"

    def _store_sql_error(self, message):
        self.error = {"message": message}

        if self._debug:
            self.error["module"] = self.__class__.__name__
            requestline = self.conn.request_line

            if isinstance(requestline, tuple):
                self.error["sql_request"] = [
                    line for line in requestline[0].split("\n") if len(line) > 0
                ]
            else:
                self.error["sql_request"] = [line for line in requestline.split("\n")]

        logger.error(self.error)

    def _get_package_dep_set(self, packages_hashes: Iterable[int], first: bool = False):
        # get binary packages hashes that provides dependencies required by
        # source packages defined by hashes form pkgs
        fpd = FindPackagesDependencies(
            self.conn,
            packages_hashes,
            "require",
            self.branch,
            self.archs,
            self._debug,
        )
        fpd.get_package_dependencies_set()

        tmp_list = set()

        for key, val in fpd.dependencies_dict.items():
            # update dependencies_tree_dict
            if key not in self.deps_tree_dict:
                self.deps_tree_dict[key] = val
            else:
                self.deps_tree_dict[key].update(val)
            # process dependencies
            if first:
                self.dependencies_dict[key] = val
                tmp_list.update(val)
            else:
                for pkg, hshs in self.dependencies_dict.items():
                    if key in hshs:
                        uniq_hshs = val - hshs
                        self.dependencies_dict[pkg].update(uniq_hshs)
                        tmp_list.update(uniq_hshs)

        if not tmp_list:
            return

        # recursive call untill all dependencies are resolved
        return self._get_package_dep_set(packages_hashes=tuple(tmp_list))

    def build_result(self):
        tmp_table = _make_table_name("all_hshs")

        if USE_SHADOW_TABLES:
            # create shadow last_depends table
            self.conn.request_line = self.sql.create_shadow_last_depends
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response)
                raise SqlRequestError(self.error)

            # fill shadow last_depends with data from current branch state
            self.conn.request_line = self.sql.fill_shadow_last_depends.format(
                branch=self.branch
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response)
                raise SqlRequestError(self.error)

        # gather package dependencies set recursively
        self._get_package_dep_set(self.source_packages_hashes, first=True)

        if USE_SHADOW_TABLES:
            # drop shadow last_depends table
            self.conn.request_line = self.sql.drop_shadow_last_depends
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response)
                raise SqlRequestError(self.error)

        self.conn.request_line = self.sql.create_tmp_table.format(tmp_table=tmp_table)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        hsh_list = self.dependencies_dict.keys() | set(
            [hsh for val in self.dependencies_dict.values() for hsh in val]
        )

        self.conn.request_line = (
            self.sql.insert_to_tmp_table.format(tmp_tbl=tmp_table),
            ((hsh,) for hsh in hsh_list),
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        # get information for all packages in hsh_dict (keys and values)
        self.conn.request_line = self.sql.get_meta_by_hshs.format(tmp_table=tmp_table)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        dict_info = dict([(tuple(r[0]), r[1:]) for r in response])

        # drop temporary table
        self.conn.request_line = self.sql.drop_tmp_table.format(tmp_table=tmp_table)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        PkgInfo = namedtuple(
            "PkgInfo", ["name", "version", "release", "epoch", "archs"]
        )
        result_list = []

        for pkg, hshs in self.dependencies_dict.items():
            counter = 0
            control_list = set()
            pkg_req_list = []

            for hsh in hshs:
                dict_info_key = [k for k in dict_info.keys() if hsh in k][0]
                dict_info_val = dict_info[dict_info_key]
                control_list_el = tuple(dict_info_val[:4])

                if control_list_el not in control_list:
                    control_list.add(control_list_el)
                    # add packages names that required by deps
                    pkg_req_list_record = PkgInfo(*dict_info_val)._asdict()
                    pkg_req_list_record["requires"] = []

                    for hsh_ in self.deps_tree_dict.get(dict_info_key[0], []):
                        pkg_ = dict_info.get((hsh_,))
                        if pkg_:
                            pkg_req_list_record["requires"].append(pkg_[0])

                    pkg_req_list.append(pkg_req_list_record)
                    counter += 1

            pkg_key = [k for k in dict_info.keys() if pkg in k][0]
            result_list.append(
                {
                    "package": dict_info[pkg_key][0],
                    "length": counter,
                    "depends": sorted(pkg_req_list, key=lambda val: val["name"]),
                }
            )

        return result_list


PROVIDE_TYPE_LUT = {"provide_src": (1,), "provide_bin": (0,), "provide_all": (0, 1)}


class FindPackagesDependencies:
    """
    Retrieves packages dependencies from database.

    Result dictionary contains mapping between package hashes.
    """

    def __init__(
        self,
        connection: ConnectionProto,
        in_packages_hashes: Iterable[int],
        dependency_type: Literal[
            "require", "provide_src", "provide_bin", "provide_all"
        ],
        branch: str,
        archs: Iterable[str],
        debug_sql: bool = False,
    ):
        self.conn = connection
        self.sql = PackageDependenciesSQL()
        self.in_packages_hashes = in_packages_hashes
        self.dependency_type = dependency_type
        self.archs = tuple(archs)
        self.branch = branch
        self.dependencies_dict: dict[int, set[int]] = {}
        self.error = ""
        self._debug = debug_sql
        self._tmp_table = _make_table_name("tmp_pkg_hshs")
        self._provide_type = PROVIDE_TYPE_LUT.get(dependency_type, (0, 1))

    def _store_sql_error(self, message):
        self.error = {"message": message}

        if self._debug:
            self.error["module"] = self.__class__.__name__
            requestline = self.conn.request_line

            if isinstance(requestline, tuple):
                self.error["sql_request"] = [
                    line for line in requestline[0].split("\n") if len(line) > 0
                ]
            else:
                self.error["sql_request"] = [line for line in requestline.split("\n")]

        logger.error(self.error)

    def _build_dependency_set(self) -> None:
        if self.dependency_type == "require":
            self.conn.request_line = self.sql.get_packages_by_requires.format(
                tmp_table=self._tmp_table, branch=self.branch, archs=self.archs
            )
        elif self.dependency_type in ("provide_src", "provide_bin", "provide_all"):
            self.conn.request_line = self.sql.get_packages_by_provides.format(
                tmp_table=self._tmp_table,
                branch=self.branch,
                archs=self.archs,
                prov_type=self._provide_type,
            )
        else:
            raise SqlRequestError(f"unknown dependency type: {self.dependency_type}")

        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        PkgDep = namedtuple("PkgDep", ["hash", "deps", "type"])

        in_packages_req: dict[int, list[Dependency]] = {}
        found_packages_req: dict[int, list[Dependency]] = {}

        if self.dependency_type == "require":
            # collect input packages `requires` and found packages `provides`
            for el in response:
                dep = PkgDep(*el)
                if dep.type == "require":
                    in_packages_req[dep.hash] = [
                        make_dependency_tuple(*x) for x in dep.deps
                    ]
                else:
                    found_packages_req[dep.hash] = [
                        make_dependency_tuple(*x) for x in dep.deps
                    ]
            # build result dependency dictionary
            for in_hsh, in_deps in in_packages_req.items():
                if in_hsh not in self.dependencies_dict:
                    self.dependencies_dict[in_hsh] = set()

                for in_d in in_deps:
                    for f_hsh, f_deps in found_packages_req.items():
                        if f_hsh in self.dependencies_dict[in_hsh]:
                            continue

                        for f_d in f_deps:
                            if checkDependencyOverlap(f_d, in_d):
                                self.dependencies_dict[in_hsh].add(f_hsh)
                                break
        else:
            raise NotImplementedError

    def get_package_dependencies_set(self) -> dict[int, set[int]]:
        # create temporary table
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=self._tmp_table
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        # insert input packages hashes
        self.conn.request_line = (
            self.sql.insert_to_tmp_table.format(tmp_tbl=self._tmp_table),
            ((hsh,) for hsh in self.in_packages_hashes),
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        self._build_dependency_set()

        # drop temporary table
        self.conn.request_line = self.sql.drop_tmp_table.format(
            tmp_table=self._tmp_table
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        return self.dependencies_dict
