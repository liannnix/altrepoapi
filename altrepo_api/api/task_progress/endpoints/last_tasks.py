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

from dataclasses import asdict

from altrepo_api.api.base import APIWorker

from ..sql import sql
from ..dto import TaskMeta, TaskApprovalMeta, SubtaskMeta, SubtaskArchsMeta


MAX_LIMIT = 10_000


class LastTasks(APIWorker):
    """
    Get information about the latest changes of build tasks.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        limit = self.args["tasks_limit"]
        if limit and (limit < 1 or limit > MAX_LIMIT):
            self.validation_results.append(
                f"tasks_limit should be in range 1 to {MAX_LIMIT}"
            )

        return self.validation_results == []

    def get(self):
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

        # get task info
        response = self.send_sql_request(
            self.sql.get_last_tasks_from_progress.format(
                branch=branch_clause,
                limit=limit_clause,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database",
                    "args": self.args,
                }
            )

        tasks = {el[0]: TaskMeta(*el) for el in response}  # type: ignore
        task_ids = [{"task_id": el} for el in tasks.keys()]

        # get task approval info by task_id
        _tmp_table = "tmp_task_ids"
        response = self.send_sql_request(
            self.sql.get_task_approval.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("task_id", "UInt32"),
                    ],
                    "data": task_ids,
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if response:
            for el in response:
                tasks[el[0]].approval.append(TaskApprovalMeta(*el[1:]))

        # get subtask info by task_id
        _tmp_table = "tmp_task_ids"
        response = self.send_sql_request(
            self.sql.get_subtasks_from_progress.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("task_id", "UInt32"),
                    ],
                    "data": task_ids,
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database",
                    "args": self.args,
                }
            )
        subtasks = {(el[0], el[1]): SubtaskMeta(*el) for el in response}

        # get subtask archs by task_id and subtask_id

        _tmp_table = "tmp_tasks_subtasks"
        response = self.send_sql_request(
            self.sql.get_subtasks_status_from_progress.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("task_id", "UInt32"),
                        ("subtask_id", "UInt32"),
                    ],
                    "data": [
                        {"task_id": el[0], "subtask_id": el[1]}
                        for el in subtasks.keys()
                    ],
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if response:
            if response:
                for el in response:
                    subtasks[(el[0], el[1])].archs = [
                        SubtaskArchsMeta(*arch) for arch in el[2]
                    ]
                    subtasks[(el[0], el[1])].type = el[3]

        for key, subtasks in subtasks.items():
            tasks[key[0]].subtasks.append(subtasks)

        res = {
            "request_args": self.args,
            "length": len(tasks.keys()),
            "tasks": [asdict(el) for el in tasks.values()],
        }
        return res, 200
