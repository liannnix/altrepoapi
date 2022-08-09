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

from collections import namedtuple

from altrepo_api.api.base import APIWorker
from ..sql import sql


class PackageVersionsFromTasks(APIWorker):
    """Retrieves packages information from last tasks."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.name = self.args["name"]
        self.branch = self.args["branch"]

        if self.branch is not None:
            branch_sub = f"WHERE task_repo = '{self.branch}'"
        else:
            self.branch = ""
            branch_sub = ""

        # get package versions from tasks
        response = self.send_sql_request(
            self.sql.get_all_src_versions_from_tasks.format(
                name=self.name, branch_sub=branch_sub
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args},
            )

        PkgVersions = namedtuple(
            "PkgVersions",
            [
                "task",
                "hash",
                "branch",
                "owner",
                "changed",
                "name",
                "version",
                "release",
            ],
        )

        pkg_versions = [PkgVersions(*el)._asdict() for el in response]
        pkg_versions.sort(key=lambda val: val["changed"], reverse=True)

        res = {
            "request_args": self.args,
            "length": len(pkg_versions),
            "versions": pkg_versions,
        }

        return res, 200
