# ALTRepo API
# Copyright (C) 2021  BaseALT Ltd

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

from collections import namedtuple

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql
from altrepo_api.utils import sort_branches, tuplelist_to_dict, dp_flags_decode


class DependsBinPackage(APIWorker):
    """Dependencies of the binary package."""

    def __init__(self, connection, pkghash, **kwargs):
        self.conn = connection
        self.pkghash = pkghash
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        self.conn.request_line = self.sql.get_depends_bin_pkg.format(
            pkghash=self.pkghash
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No found",
                    "args": self.pkghash,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgDependencies = namedtuple(
            "PkgDependencies", ["name", "version", "flag", "type"]
        )
        pkg_dependencies = [PkgDependencies(*el)._asdict() for el in response]

        # change numeric flag on text
        for el in pkg_dependencies:
            el["flag_decoded"] = dp_flags_decode(el["flag"], lut.rpmsense_flags)

        # get package name and arch
        self.conn.request_line = self.sql.get_pkgs_name_and_arch.format(
            pkghash=self.pkghash
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        # get package versions
        pkg_versions = []
        self.conn.request_line = self.sql.get_pkg_binary_versions.format(
            name=response[0][0], arch=response[0][1]
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        PkgVersions = namedtuple(
            "PkgVersions", ["branch", "version", "release", "pkghash"]
        )
        # sort package versions by branch
        pkg_branches = sort_branches([el[0] for el in response])
        pkg_versions = tuplelist_to_dict(response, 3)  # type: ignore

        pkg_versions = [
            PkgVersions(*(b, *pkg_versions[b][-3:]))._asdict() for b in pkg_branches
        ]

        res = {
            "request_args": self.pkghash,
            "length": len(pkg_dependencies),
            "dependencies": pkg_dependencies,
            "versions": pkg_versions,
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
        dp_name = self.args["dp_name"]
        dp_type = self.args["dp_type"]
        branch = self.args["branch"]

        self.conn.request_line = self.sql.get_pkgs_depends.format(
            dp_name=dp_name,
            branch=branch,
            dp_type=dp_type,
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No packages found in last packages with hash",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error
        pkg_hash = response

        # create temporary table with pkg_hash
        tmp_table = "tmp_pkghash"
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table, columns="(pkg_hash UInt64)"
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        # insert pkg_hash into temporary table
        self.conn.request_line = (
            self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
            (
                {
                    "pkg_hash": el[0],
                }
                for el in pkg_hash
            ),
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        self.conn.request_line = self.sql.get_repo_packages.format(
            tmp_table=tmp_table, branch=branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No data found in database for given parameters",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "hash",
                "name",
                "version",
                "release",
                "arch",
                "sourcepackage",
                "buildtime",
                "summary",
                "maintainer",
                "category",
            ],
        )

        retval = [PkgMeta(*el)._asdict() for el in response]

        for el in retval:
            if el["sourcepackage"] == 1:
                el["arch"] = "source"

        # get pkgsetname dependency
        all_branches = []
        self.conn.request_line = self.sql.get_pkgset_depends.format(
            dp_name=dp_name, dp_type=dp_type
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        PkgCount = namedtuple("PkgCount", ["branch", "count"])
        # sort package counts by branch
        pkg_branches = sort_branches([el[1] for el in response])
        pkg_counts = {el[1]: el[0] for el in response}
        all_branches = [PkgCount(*(b, pkg_counts[b]))._asdict() for b in pkg_branches]

        res = {
            "request_args": self.args,
            "length": len(retval),
            "packages": retval,
            "branches": all_branches,
        }
        return res, 200


class DependsSrcPackage(APIWorker):
    """Dependencies of the source package."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["depth"] is not None and self.args["depth"] != 1:
            self.validation_results.append(
                f"Depth level other than 1 is not supported yet"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        branch = self.args["branch"]
        depth = self.args["depth"]
        if depth is None:
            depth = 1

        # get package info
        self.conn.request_line = self.sql.get_pkg_info.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No data found in database for given parameters",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgInfo = namedtuple(
            "PkgInfo", ["name", "epoch", "version", "release", "buildtime"]
        )

        pkg_info = PkgInfo(*response[0])

        # build dependencies
        tmp_table = "_TmpSrcDepends"
        self.conn.request_line = self.sql.make_src_depends_tmp.format(
            tmp_table=tmp_table, pkghash=self.pkghash
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        # read binary dependencies
        self.conn.request_line = self.sql.select_all_tmp_table.format(tmp_table=tmp_table)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        PkgDependencies = namedtuple("PkgDependencies", ["name", "version", "flag"])
        pkg_dependencies = [PkgDependencies(*el)._asdict() for el in response]

        for el in pkg_dependencies:
            el["type"] = "require"
            el["flag_decoded"] = dp_flags_decode(el["flag"], lut.rpmsense_flags)

        # get source packages from last branch state by dependency names
        tmp_table_2 = "_TmpSrcByBinDeps"
        self.conn.request_line = self.sql.make_src_by_bin_deps_tmp.format(
            tmp_table_2=tmp_table_2, tmp_table=tmp_table, branch=branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        self.conn.request_line = self.sql.get_src_by_bin_deps.format(
            tmp_table=tmp_table_2
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        SrcPkgInfo = namedtuple("SrcPkgInfo", ["pkghash", "name", "version", "release", "summary"])
        src_pkg_dependencies = [SrcPkgInfo(*el)._asdict() for el in response]
        for pkg in src_pkg_dependencies:
            pkg["pkghash"] = str(pkg["pkghash"])

        # drop temporary table
        self.conn.request_line = self.sql.drop_tmp_table.format(tmp_table=tmp_table)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        self.conn.request_line = self.sql.drop_tmp_table.format(tmp_table=tmp_table_2)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        res = {
            "request_args": self.args,
            "length": len(src_pkg_dependencies),
            "package_info": pkg_info._asdict(),
            "dependencies": pkg_dependencies,
            "provided_by_src": src_pkg_dependencies,
        }
        return res, 200
