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

from dataclasses import dataclass
from collections import namedtuple
from typing import Iterable, Union

from altrepo_api.api.base import ConnectionProto
from altrepo_api.utils import get_logger

from .exceptions import SqlRequestError

logger = get_logger(__name__)


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

    get_srchsh_for_binary = """
SELECT DISTINCT
    srchsh,
    groupUniqArray(pkg_hash)
FROM
(
    SELECT
        pkg_hash AS srchsh,
        dp_name
    FROM Depends
    WHERE pkg_hash IN {pkgs}
        AND dp_type = 'require'
) AS sourceDep
INNER JOIN
(
    SELECT
        pkg_hash,
        dp_name
    FROM last_depends
    WHERE dp_type = 'provide'
        AND pkgset_name = '{branch}'
        AND pkg_sourcepackage = 0
        AND pkg_arch IN {archs}
) AS binaryDeps USING dp_name
GROUP BY srchsh
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
        self.dependencies_dict = {}
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

    def _get_package_dep_set(
        self, pkgs_hshs_sql_clause: Union[str, Iterable[int]], first: bool = False
    ):
        # get binary packages hashes that provides dependencies required by
        # source packages defined by hashes form pkgs
        self.conn.request_line = self.sql.get_srchsh_for_binary.format(
            pkgs=pkgs_hshs_sql_clause, branch=self.branch, archs=tuple(self.archs)
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        tmp_list = []

        for key, val in response:
            # update dependencies_tree_dict
            if key not in self.deps_tree_dict:
                self.deps_tree_dict[key] = set(val)
            else:
                self.deps_tree_dict[key].update(val)
            # process dependencies
            if first:
                self.dependencies_dict[key] = val
                tmp_list += list(set(val) - set(tmp_list))
            else:
                for pkg, hshs in self.dependencies_dict.items():
                    hshs_set = set(hshs)
                    if key in hshs_set:
                        uniq_hshs = list(set(val) - hshs_set)
                        self.dependencies_dict[pkg] += uniq_hshs
                        tmp_list += uniq_hshs

        self.conn.request_line = self.sql.drop_tmp_table.format(
            tmp_table=self._tmp_table
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=self._tmp_table
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        self.conn.request_line = (
            self.sql.insert_to_tmp_table.format(tmp_tbl=self._tmp_table),
            ((hsh,) for hsh in tmp_list),
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        if not tmp_list:
            return

        # recursive call untill all dependencies are resolved
        return self._get_package_dep_set(
            pkgs_hshs_sql_clause=self.sql.select_from_tmp_table.format(
                tmp_table=self._tmp_table
            )
        )

    def build_result(self):
        tmp_table = "all_hshs"

        self._get_package_dep_set(self.source_packages_hashes, first=True)

        # print(f"DBG: {self.deps_tree_dict}")
        # print(f"DBG: {self.dependencies_dict}")

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
