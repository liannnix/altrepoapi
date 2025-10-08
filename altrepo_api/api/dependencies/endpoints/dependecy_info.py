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

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.api.task.endpoints.task_repo import LastRepoStateFromTask
from altrepo_api.utils import dp_flags_decode, make_tmp_table_name, sort_branches

from ..sql import sql


class DependsBinPackage(APIWorker):
    """Dependencies of the binary package."""

    def __init__(self, connection, pkg_hash, **kwargs):
        self.conn = connection
        self.pkg_hash = pkg_hash
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(
            self.sql.get_depends_bin_pkg.format(pkg_hash=self.pkg_hash)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database",
                    "args": self.pkg_hash,
                }
            )

        pkg_dependencies = [
            {
                "name": name,
                "version": version,
                "flag": flag,
                # change numeric flag on text
                "flag_decoded": dp_flags_decode(flag, lut.rpmsense_flags),
                "type": type,
            }
            for name, version, flag, type in response
        ]

        res = {
            "request_args": str(self.pkg_hash),
            "length": len(pkg_dependencies),
            "dependencies": pkg_dependencies,
        }
        return res, 200


class PackagesDependence(APIWorker):
    """Retrieves binary packages by dependency name and type."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        dp_name: str = self.args["dp_name"]
        dp_type: str = self.args["dp_type"]
        branch: str = self.args["branch"]
        last_state: bool = self.args["last_state"]

        dp_type_where_clause = f"AND dp_type = '{dp_type}'" if dp_type != "all" else ""

        sql_format_args = {
            "dp_name": dp_name,
            "dp_type_where_clause": dp_type_where_clause,
            "table_name": "static_last_packages",
            "branch_where_clause": f"WHERE pkgset_name = '{branch}'",
        }
        sql_args = {}

        if last_state:
            ls = LastRepoStateFromTask(self.conn, branch)
            ls.build_repo_state()
            if not ls.status:
                return ls.error

            if ls.task_repo_pkgs:
                # if ls.task_repo_pkgs is None -> can't find last pkgset state packages
                # in most cases it means no tasks commited after branch commit

                tmp_table_name = make_tmp_table_name("tmp_pkg_hash")

                sql_format_args.update(
                    {"table_name": tmp_table_name, "branch_where_clause": ""}
                )

                sql_args["external_tables"] = (
                    [
                        {
                            "name": tmp_table_name,
                            "structure": [("pkg_hash", "UInt64")],
                            "data": [{"pkg_hash": hash} for hash in ls.task_repo_pkgs],  # type: ignore
                        },
                    ],
                )

        response = self.send_sql_request(
            self.sql.get_pkgs_depends.format(**sql_format_args),
            **sql_args,
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

        pkg_dp_types: dict[int, list[str]] = {
            pkg_hash: dp_types for pkg_hash, dp_types in response
        }

        # create temporary table with pkg_hash
        tmp_table = make_tmp_table_name("tmp_pkg_hash")
        _ = self.send_sql_request(
            self.sql.create_tmp_table.format(
                tmp_table=tmp_table, columns="(pkg_hash UInt64)"
            )
        )
        if not self.sql_status:
            return self.error

        # insert pkg_hash into temporary table
        _ = self.send_sql_request(
            (
                self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
                ({"pkg_hash": el} for el in pkg_dp_types),
            )
        )
        if not self.sql_status:
            return self.error

        response = self.send_sql_request(
            self.sql.get_repo_packages.format(tmp_table=tmp_table, branch=branch)
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

        retval = [
            {
                "hash": hash,
                "name": name,
                "version": version,
                "release": release,
                "arch": arch if not sourcepackage else "source",
                "sourcepackage": sourcepackage,
                "buildtime": buildtime,
                "summary": summary,
                "maintainer": maintainer,
                "category": category,
                "dp_types": pkg_dp_types.get(hash, []),
            }
            for (
                hash,
                name,
                version,
                release,
                arch,
                sourcepackage,
                buildtime,
                summary,
                maintainer,
                category,
            ) in response
        ]

        # get pkgsetname dependency
        response = self.send_sql_request(
            self.sql.get_pkgset_depends.format(
                dp_name=dp_name, dp_type=dp_type_where_clause
            )
        )
        if not self.sql_status:
            return self.error

        # sort package counts by branch
        sorted_branches = sort_branches([branch for _, branch in response])  # type: ignore
        branches_statistics = {branch: count for count, branch in response}  # type: ignore
        branches_stats = [
            {"branch": branch, "count": branches_statistics[branch]}
            for branch in sorted_branches
        ]

        res = {
            "request_args": self.args,
            "length": len(retval),
            "packages": retval,
            "branches": branches_stats,
        }
        return res, 200


class DependsSrcPackage(APIWorker):
    """Dependencies of the source package."""

    def __init__(self, connection, pkg_hash, **kwargs):
        self.pkg_hash = pkg_hash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug("args : %s", self.args)
        self.validation_results = []

        if self.args["depth"] is not None and self.args["depth"] != 1:
            self.validation_results.append(
                "Depth level other than 1 is not supported yet"
            )

        return self.validation_results == []

    def get(self):
        branch = self.args["branch"]
        depth = self.args["depth"]
        if depth is None:
            depth = 1

        # get package info
        response = self.send_sql_request(
            self.sql.get_pkg_info.format(pkg_hash=self.pkg_hash)
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

        pkg_name, pkg_epoch, pkg_version, pkg_release, pkg_buildtime = response[0]
        pkg_info = {
            "name": pkg_name,
            "epoch": pkg_epoch,
            "version": pkg_version,
            "release": pkg_release,
            "buildtime": pkg_buildtime,
        }  # type: ignore

        # build dependencies
        tmp_table = make_tmp_table_name("src_depends")
        _ = self.send_sql_request(
            self.sql.make_src_depends_tmp.format(
                tmp_table=tmp_table, pkg_hash=self.pkg_hash
            )
        )
        if not self.sql_status:
            return self.error

        # read binary dependencies
        response = self.send_sql_request(
            self.sql.select_all_tmp_table.format(tmp_table=tmp_table)
        )
        if not self.sql_status:
            return self.error

        pkg_dependencies = [
            {
                "name": name,
                "version": version,
                "flag": flag,
                "flag_decoded": dp_flags_decode(flag, lut.rpmsense_flags),
                "type": "require",
            }
            for name, version, flag in response
        ]  # type: ignore

        # get source packages from last branch state by dependency names
        tmp_table_2 = make_tmp_table_name("src_by_bin_deps")
        _ = self.send_sql_request(
            self.sql.make_src_by_bin_deps_tmp.format(
                tmp_table_2=tmp_table_2, tmp_table=tmp_table, branch=branch
            )
        )
        if not self.sql_status:
            return self.error

        response = self.send_sql_request(
            self.sql.get_src_by_bin_deps.format(tmp_table=tmp_table_2)
        )
        if not self.sql_status:
            return self.error

        src_pkg_dependencies = [
            {
                "pkghash": str(hash),
                "name": name,
                "version": version,
                "release": release,
                "summary": summary,
            }
            for hash, name, version, release, summary in response
        ]  # type: ignore

        # drop temporary table
        _ = self.send_sql_request(self.sql.drop_tmp_table.format(tmp_table=tmp_table))
        if not self.sql_status:
            return self.error

        _ = self.send_sql_request(self.sql.drop_tmp_table.format(tmp_table=tmp_table_2))
        if not self.sql_status:
            return self.error

        res = {
            "request_args": self.args,
            "length": len(src_pkg_dependencies),
            "package_info": pkg_info,
            "dependencies": pkg_dependencies,
            "provided_by_src": src_pkg_dependencies,
        }
        return res, 200
