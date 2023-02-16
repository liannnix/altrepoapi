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

from altrepo_api.utils import get_logger, join_tuples
from altrepo_api.api.base import APIWorker
from altrepo_api.api.base import ConnectionProtocol
from altrepo_api.libs.package_dependencies import PackageDependencies
from altrepo_api.libs.exceptions import SqlRequestError
from ..sql import sql


class BuildDependencySet(APIWorker):
    """Retrieves source package build dependencies recursively."""

    def __init__(
        self,
        connection: ConnectionProtocol,
        packages: list[str],
        branch: str,
        archs: list[str],
        **kwargs,
    ):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.packages = tuple(packages)
        self.branch = branch
        self.archs = archs
        self.result = (list(), list())
        # add 'noarch' to archs list
        if "noarch" not in self.archs:
            self.archs += ["noarch"]
        super().__init__()

    def build_dependency_set(self):
        # get source packages hashes by names
        response = self.send_sql_request(
            self.sql.get_pkg_hshs.format(pkgs=self.packages, branch=self.branch)
        )
        if not self.sql_status:
            return
        if not response:
            _ = self.store_error(
                {
                    "message": f"Source packages {list(self.packages)} not found in package set '{self.branch}'"
                }
            )
            return

        hshs = join_tuples(response)  # type: ignore

        pkg_deps = PackageDependencies(
            self.conn, hshs, self.branch, self.archs, self.DEBUG
        )

        try:
            self.result = pkg_deps.build_result()
        except SqlRequestError as e:
            _ = self.store_error(
                {
                    "message": "Error occured in ConflictFilter",
                    "error": e.error_details,
                },
                self.LL.ERROR,
                500,
            )
            return

        self.status = True


class PackageBuildDependencySet(APIWorker):
    """Retrieves source packages build dependencies."""

    def __init__(self, connection: ConnectionProtocol, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.logger = get_logger(__name__)

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        # arguments processing
        if self.args["arch"] is None:
            archs = ["x86_64"]
        else:
            archs = [self.args["arch"]]
        # init BuildDependency class with args
        self.bds = BuildDependencySet(
            self.conn, self.args["packages"], self.args["branch"], archs
        )
        # build result
        self.bds.build_dependency_set()

        # format result
        if self.bds.status:
            dep_packages, ambiguous_depends = self.bds.result
            res = {
                "request_args": self.args,
                "length": len(dep_packages),
                "packages": dep_packages,
                "ambiguous_dependencies": ambiguous_depends,
            }
            return res, 200
        else:
            return self.bds.error
