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
import datetime
from dataclasses import dataclass, asdict, field

from altrepo_api.api.base import APIWorker
from ..sql import sql


@dataclass
class SubtaskArchsMeta:
    arch: str
    stage_status: str


@dataclass
class SubtaskMeta:
    task_id: int
    subtask_id: int
    subtask_type: str
    subtask_srpm: str
    subtask_srpm_name: str
    subtask_srpm_evr: str
    subtask_dir: str
    subtask_tag_id: str
    subtask_tag_name: str
    subtask_tag_author: str
    subtask_package: str
    subtask_pkg_from: str
    subtask_changed: datetime.datetime
    type: str
    archs: list[SubtaskArchsMeta] = field(default_factory=list)


@dataclass
class TaskMeta:
    task_id: int
    task_repo: str
    task_state: str
    task_owner: str
    task_try: int
    task_iter: int
    task_changed: str
    task_message: str
    task_stage: str
    subtasks: list[SubtaskMeta] = field(default_factory=list)


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

        if self.args["tasks_limit"] and self.args["tasks_limit"] < 1:
            self.validation_results.append(
                "tasks_limit should be greater or equal to 1"
            )

        if self.validation_results != []:
            return False
        else:
            return True

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
            self.sql.get_last_tasks.format(
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

        tasks = [TaskMeta(*el) for el in response]  # type: ignore

        # get subtask info by task_id
        _tmp_table = "tmp_task_ids"
        response = self.send_sql_request(
            self.sql.get_subtasks.format(tmp_table=_tmp_table),
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
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database",
                    "args": self.args,
                }
            )
        subtasks = [SubtaskMeta(*el) for el in response]

        # get subtask archs by task_id and subtask_id
        _tmp_table = "tmp_tasks_subtasks"
        tasks_subtasks = []
        for task in tasks:
            for sub in subtasks:
                if task.task_state in ("BUILDING", "FAILED", "FAILING"):
                    if task.task_id == sub.task_id:
                        tasks_subtasks.append(
                            {
                                "task_id": sub.task_id,
                                "subtask_id": sub.subtask_id
                            }
                        )

        response = self.send_sql_request(
            self.sql.get_subtasks_status.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("task_id", "UInt32"),
                        ("subtask_id", "UInt32"),
                    ],
                    "data": tasks_subtasks,
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if response:
            for subtask in subtasks:
                for el in response:
                    if el[0] == subtask.task_id and el[1] == subtask.subtask_id:
                        subtask.archs = [SubtaskArchsMeta(*arch) for arch in el[2]]
                        subtask.type = el[3]

        for task in tasks:
            task.subtasks = [el for el in subtasks if el.task_id == task.task_id]

        res = {
            "request_args": self.args,
            "length": len(tasks),
            "tasks": [asdict(el) for el in tasks],
        }
        return res, 200
