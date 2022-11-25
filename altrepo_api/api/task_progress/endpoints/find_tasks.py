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
from dataclasses import dataclass, asdict

from altrepo_api.api.base import APIWorker
from ..sql import sql


@dataclass
class TaskMeta:
    task_id: int
    task_owner: str
    task_repo: str
    task_state: str
    components: list[str]


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
            where_clause = f"subtask_id = 0 AND toString(task_id) LIKE '%{input_val}%'"
        else:
            where_clause = (
                f"task_owner ILIKE '%{input_val}%' OR "
                f"splitByChar('/', subtask_package)[-1] ILIKE '%{input_val}%'"
            )

        response = self.send_sql_request(
            self.sql.task_search_fast_lookup.format(
                branch=branch_clause, where=where_clause, limit=limit_clause
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        def process_task_components(components: list[str]) -> list[str]:
            result = []
            for c in components:
                if c == "":
                    continue
                c = c.rstrip(".git").split("/")[-1]
                result.append(c)
            return result

        tasks = []
        for task in [TaskMeta(*el[:-1]) for el in response]:
            task.components = process_task_components(task.components)
            if task.task_state != 'DELETED':
                tasks.append(task)

        res = {
            "request_args": self.args,
            "length": len(tasks),
            "tasks": [asdict(el) for el in tasks],
        }
        return res, 200
