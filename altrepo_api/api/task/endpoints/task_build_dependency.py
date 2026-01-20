# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

from altrepo_api.settings import namespace as settings
from altrepo_api.utils import valid_task_id
from altrepo_api.api.base import APIWorker
from altrepo_api.api.package.endpoints.pkg_build_dependency import BuildDependency

from .task_repo import TaskRepoState
from ..sql import sql


class TaskBuildDependency(APIWorker):
    """Retrieves information for packages dependent on packages from task."""

    def __init__(self, connection, id, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id
        super().__init__()

    def check_task_id(self):
        if not valid_task_id(self.task_id):
            return False
        response = self.send_sql_request(self.sql.check_task.format(id=self.task_id))
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["depth"] < 1 or self.args["depth"] > settings.DEPENDENCY_MAX_DEPTH:
            self.validation_results.append(
                f"dependency depth should be in range (1...{settings.DEPENDENCY_MAX_DEPTH})"
            )

        if None not in (self.args["filter_by_source"], self.args["filter_by_package"]):
            self.validation_results.append(
                "Parameters 'filter_by_src' and 'filter_by_package' can't be used together"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        # arguments processing
        self.args["package"] = []
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
            self.sql.build_task_src_packages.format(id=self.task_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No source packages found for task '{self.task_id}'"},
            )

        self.args["package"] = list({pkg[0] for pkg in response})

        # get task repo state
        tr = TaskRepoState(self.conn, self.task_id)
        tr.build_task_repo(keep_artefacts=False)
        if not tr.status:
            return tr.error

        # init BuildDependency class with args
        bd = BuildDependency(
            self.conn,
            self.args["package"],
            self.args["branch"],
            self.args["archs"],
            self.args["leaf"],
            self.args["depth"],
            self.args["dptype"],
            self.args["filter_by_package"],
            self.args["filter_by_source"],
            self.args["finite_package"],
            self.args["oneandhalf"],
        )

        # build result
        bd.build_dependencies(task_repo_hashes=tr.task_repo_pkgs)

        # set flag if task plan is applied to repository state
        self.args["task_plan_applied"] = tr.have_plan

        # format result
        if bd.status:
            # result processing
            res = {
                "id": self.task_id,
                "request_args": self.args,
                "length": len(bd.result),
                "dependencies": bd.result,
            }
            return res, 200
        else:
            return bd.error
