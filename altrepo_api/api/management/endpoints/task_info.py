# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

from altrepo_api.api.base import APIWorker

from ..sql import sql


@dataclass
class SubtaskMeta:
    task_id: int
    subtask_id: int
    subtask_changed: datetime
    src_pkg_hash: str
    src_pkg_name: str
    src_pkg_version: str
    src_pkg_release: str
    chlog_text: str
    chlog_date: datetime
    chlog_name: str
    chlog_evr: str
    errata_id: str
    is_discarded: bool
    eh_created: datetime
    eh_update: datetime
    errata_id: str
    vulnerabilities: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TaskMeta:
    task_id: int
    task_repo: str
    task_state: str
    task_changed: datetime
    task_message: str
    task_owner: str
    subtasks: list[SubtaskMeta] = field(default_factory=list)


class TaskInfo(APIWorker):
    """
    Get information about the task and a list
    of vulnerabilities for subtasks based on task ID.
    """

    def __init__(self, connection, id_, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id_
        super().__init__()

    def check_task_id(self):
        """
        Check if the task exists in the DB.
        """
        response = self.send_sql_request(self.sql.check_task.format(id=self.task_id))
        if not self.sql_status:
            return False
        return response[0][0] != 0

    def get(self):
        # get task info (exclude tasks, if in all subtasks removed packages)
        response = self.send_sql_request(self.sql.get_task_info.format(id=self.task_id))
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )
        task_info = TaskMeta(*response[0])

        # get subtasks info by task_id
        response = self.send_sql_request(
            self.sql.get_subtasks_by_task_id.format(
                task_id=self.task_id, branch=task_info.task_repo
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        for el in response:
            subtask = SubtaskMeta(*el[:-2])
            subtask.vulnerabilities = [
                {"id": v, "type": t} for t, v in zip(el[-1], el[-2])
            ]
            task_info.subtasks.append(subtask)

        return asdict(task_info), 200
