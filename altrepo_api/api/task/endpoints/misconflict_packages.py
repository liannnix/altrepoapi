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

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql
from .task_repo import TaskRepoState
from altrepo_api.api.package.endpoints.misconflict_packages import MisconflictPackages


class TaskMisconflictPackages(APIWorker):
    """Retrives packages with file conflicts."""

    def __init__(self, connection, id, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id
        super().__init__()

    def check_task_id(self):
        self.conn.request_line = self.sql.check_task.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.INFO, 500)
            return False

        if response[0][0] == 0:
            return False
        return True

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        # arguments processing
        self.args["packages"] = []
        self.args["branch"] = None
        # get task source packages and branch
        # get task repo
        self.conn.request_line = self.sql.task_repo.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data found in database for task '{self.task_id}'"},
                self.ll.INFO,
                404,
            )
            return self.error

        self.args["branch"] = response[0][0]
        # get task source packages
        self.conn.request_line = self.sql.misconflict_get_pkgs_of_task.format(
            id=self.task_id
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No packages found in database for task '{self.task_id}'"},
                self.ll.INFO,
                404,
            )
            return self.error
        self.args["packages"] = tuple({pkg[0] for pkg in response})
        pkg_hashes = tuple({pkg[1] for pkg in response})
        # get task repo state
        tr = TaskRepoState(self.conn, self.task_id)
        tr.build_task_repo(keep_artefacts=False)
        if not tr.status:
            return tr.error
        # init MisconflictPackages class with args
        mp = MisconflictPackages(
            self.conn,
            self.args["packages"],
            self.args["branch"].lower(),
            self.args["archs"],
        )

        # build result
        mp.find_conflicts(pkg_hashes=pkg_hashes, task_repo_hashes=tr.task_repo_pkgs)  # type: ignore

        # format result
        if mp.status:
            # result processing
            res = {
                "id": self.task_id,
                "request_args": self.args,
                "length": len(mp.result),
                "conflicts": mp.result,
            }
            return res, 200
        else:
            return mp.error
