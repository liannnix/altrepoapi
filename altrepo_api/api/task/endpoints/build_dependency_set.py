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

from altrepo_api.api.base import APIWorker
from ..sql import sql
from altrepo_api.api.package.endpoints.build_dependency_set import BuildDependencySet


class TaskBuildDependencySet(APIWorker):
    """Retrieves task packages build dependencies."""

    def __init__(self, connection, id, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id
        super().__init__()

    def check_task_id(self):
        response = self.send_sql_request(self.sql.check_task.format(id=self.task_id))
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        # arguments processing
        if self.args["arch"] is None:
            archs = ["x86_64"]
        else:
            archs = [self.args["arch"]]
        self.args["packages"] = []
        self.args["branch"] = None

        # get task source packages and branch
        # get task repo
        response = self.send_sql_request(self.sql.task_repo.format(id=self.task_id))
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No data found in database for task '{self.task_id}'"}
            )

        self.args["branch"] = response[0][0]  # type: ignore

        # get task source packages
        response = self.send_sql_request(
            self.sql.task_src_packages.format(id=self.task_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No packages found in database for task '{self.task_id}'"}
            )

        self.args["packages"] = [pkg[0] for pkg in response]

        # FIXME: BuildDependencySet class uses last branch state instead of
        # actual branch state which could return misleading results here
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
                "id": self.task_id,
                "request_args": self.args,
                "length": len(dep_packages),
                "packages": dep_packages,
                "ambiguous_dependencies": ambiguous_depends,
            }
            return res, 200
        else:
            return self.bds.error
