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
from dataclasses import asdict

from altrepo_api.api.base import APIWorker
from ..dto import (
    TaskMeta,
    IterationMeta,
    TaskApprovalMeta,
    SubtaskMeta,
    SubtaskArchsMeta,
)
from ..sql import sql


class TaskInfo(APIWorker):
    def __init__(self, connection, id_, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id_
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
        response = self.send_sql_request(
            self.sql.get_task_table.format(id=self.task_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        table_name = response[0][0]

        if table_name == "progress":
            task_info = self.send_sql_request(
                self.sql.get_task_info_from_progress.format(id=self.task_id)
            )
            subtask_list = self.send_sql_request(
                self.sql.get_subtasks_by_id_from_progress.format(id=self.task_id)
            )
        else:
            task_info = self.send_sql_request(
                self.sql.get_task_info_from_state.format(id=self.task_id)
            )
            subtask_list = self.send_sql_request(
                self.sql.get_subtasks_by_id_from_state.format(id=self.task_id)
            )

        if not self.sql_status:
            return self.error
        if not task_info:
            return self.store_error(
                {"message": "No data not found in database"},
            )
        task = TaskMeta(*task_info[0][:-1])
        task.iterations = [
            IterationMeta(*el) for el in sorted(task_info[0][-1], reverse=True)
        ]

        if subtask_list:
            subtasks = {el[1]: SubtaskMeta(*el) for el in subtask_list}

            if table_name == "progress":
                response = self.send_sql_request(
                    self.sql.get_subtasks_status_by_id_from_progress.format(
                        id=self.task_id, sub_ids=tuple(subtasks.keys())
                    )
                )
            else:
                response = self.send_sql_request(
                    self.sql.get_subtasks_status_by_id_from_state.format(
                        id=self.task_id, sub_ids=tuple(subtasks.keys())
                    )
                )

            if not self.sql_status:
                return self.error
            if response:
                for el in response:
                    subtasks[el[1]].archs = [SubtaskArchsMeta(*arch) for arch in el[2]]
                    subtasks[el[1]].type = el[3]

                # get task approval info by task_id
                _tmp_table = "tmp_task_id"
                response = self.send_sql_request(
                    self.sql.get_subtask_approval.format(tmp_table=_tmp_table),
                    external_tables=[
                        {
                            "name": _tmp_table,
                            "structure": [
                                ("task_id", "UInt32"),
                            ],
                            "data": [{"task_id": self.task_id}],
                        }
                    ],
                )
                if response:
                    for el in response:
                        subtasks[el[1]].approval = [
                            TaskApprovalMeta(*apr) for apr in el[2]
                        ]

            for subtask in subtasks.values():
                task.subtasks.append(subtask)

        res = asdict(task)

        return res, 200
