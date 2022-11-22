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
from dataclasses import dataclass, asdict, field

from altrepo_api.api.base import APIWorker
from ..sql import sql


@dataclass
class TaskComponentsMeta:
    task_id: int
    subtask_srpm: str
    subtask_srpm_name: str
    subtask_srpm_evr: str
    subtask_dir: str
    subtask_tag_name: str
    subtask_package: str


@dataclass
class TaskMeta:
    task_id: int
    task_owner: str
    task_repo: str
    task_state: str
    components: list[TaskComponentsMeta] = field(default_factory=list)


class FastTasksSearchLookup(APIWorker):
    """
    Fast tasks search lookup by id, owner or components.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["tasks_limit"] and self.args["tasks_limit"] < 1:
            self.validation_results.append(
                "tasks_limit should be greater or equal to 1"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        input_val = self.args["input"]
        branch = self.args["branch"]
        tasks_limit = self.args["tasks_limit"]

        if tasks_limit:
            limit_clause = f"LIMIT {tasks_limit}"
        else:
            limit_clause = ""

        if branch:
            branch_clause = f"AND task_repo = '{branch}'"
        else:
            branch_clause = ""

        if input_val.isdigit():
            # find tasks by ID
            response = self.send_sql_request(
                self.sql.get_tasks_by_id.format(
                    branch=branch_clause, task_id=input_val, limit=limit_clause
                )
            )
        else:
            # check the owner in the database
            response = self.send_sql_request(
                self.sql.check_owner.format(owner=input_val)
            )
            if not self.sql_status:
                return self.error
            if response:
                # find tasks by owners
                response = self.send_sql_request(
                    self.sql.get_tasks_by_owner.format(
                        branch=branch_clause, owner=input_val, limit=limit_clause
                    )
                )
            else:
                # find tasks by components
                response = self.send_sql_request(
                    self.sql.get_tasks_by_comp.format(
                        branch=branch_clause, comp=input_val, limit=limit_clause
                    )
                )

        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        tasks = [TaskMeta(*el[:-1]) for el in response]

        # get task components
        _tmp_table = "tmp_task_ids"
        response = self.send_sql_request(
            self.sql.get_task_components.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("task_id", "UInt32"),
                    ],
                    "data": [
                        {
                            "task_id": el.task_id,
                        }
                        for el in tasks
                    ],
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if response:
            components = [TaskComponentsMeta(*el) for el in response]
            for task in tasks:
                task.components = [
                    el for el in components if el.task_id == task.task_id
                ]

        res = {
            "request_args": self.args,
            "length": len(tasks),
            "tasks": [asdict(el) for el in tasks],
        }
        return res, 200
