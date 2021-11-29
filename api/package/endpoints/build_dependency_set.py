# altrepodb API
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

from utils import get_logger, join_tuples

from api.base import APIWorker
from api.misc import lut
from ..sql import sql
from libs.package_dependencies import PackageDependencies
from libs.exceptions import SqlRequestError


class BuildDependencySet(APIWorker):
    """Retrieves package build dependencies."""

    def __init__(self, connection, packages, branch, archs, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.packages = tuple(packages)
        self.branch = branch
        self.archs = archs
        self.result = []
        # add 'noarch' to archs list
        if "noarch" not in self.archs:
            self.archs += ["noarch"]
        super().__init__()

    def build_dependency_set(self):
        self.conn.request_line = self.sql.get_pkg_hshs.format(
            pkgs=self.packages, branch=self.branch
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return
        if not response:
            self._store_error(
                {
                    "message": f"Packages {list(self.packages)} not found in package set '{self.branch}'"
                },
                self.ll.INFO,
                404,
            )
            return

        hshs = join_tuples(response)

        pkg_deps = PackageDependencies(
            self.conn, hshs, self.branch, self.archs, self.DEBUG
        )

        try:
            self.result = pkg_deps.build_result()
        except SqlRequestError as e:
            self._store_error(
                {
                    "message": f"Error occured in ConflictFilter",
                    "error": e.error_details,
                },
                self.ll.ERROR,
                500,
            )
            return

        self.status = True
        return


class PackageBuildDependencySet:
    """Retrieves packages build dependencies."""
    
    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.validation_results = None
        self.logger = get_logger(__name__)

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        for pkg in self.args["packages"]:
            if pkg == "":
                self.validation_results.append(
                    "package list should not contain empty values"
                )
                break

        if self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.args["archs"]:
            for arch in self.args["archs"]:
                if arch not in lut.known_archs:
                    self.validation_results.append(f"unknown package arch : {arch}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        # arguments processing
        if self.args["archs"] is None:
            self.args["archs"] = ["x86_64"]
        # init BuildDependency class with args
        self.bds = BuildDependencySet(
            self.conn, self.args["packages"], self.args["branch"], self.args["archs"]
        )
        # build result
        self.bds.build_dependency_set()

        # format result
        if self.bds.status:
            # result processing
            res = {
                "request_args": self.args,
                "length": len(self.bds.result),
                "packages": self.bds.result,
            }
            return res, 200
        else:
            return self.bds.error
