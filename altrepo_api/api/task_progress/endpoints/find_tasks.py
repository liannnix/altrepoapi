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
from altrepo_api.api.misc import lut
from ..sql import sql
from ..dto import (
    FastSearchTaskMeta,
    TaskMeta,
    TaskState2,
    TaskApprovalMeta,
    SubtaskMeta,
    SubtaskArchsMeta,
)


class FindTasksLookup(APIWorker):
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

        if self.args["input"] and len(self.args["input"]) > 4:
            self.validation_results.append(
                "input values list should contain no more than 4 elements"
            )

        if self.validation_results != []:
            return False
        return True

    def get(self):
        input_val: list[str] = self.args["input"][:] if self.args["input"] else []
        branch = self.args["branch"]
        tasks_limit = self.args["tasks_limit"]

        branch_clause = ""
        owner_clause = ""
        state_clause = ""
        # filter out deleted tasks  by default
        where_clause = "WHERE type = 'task'"
        where_clause2 = "WHERE search NOT LIKE '%|DELETED|%' "

        # parse input values and look for owner name (prefixed by '@')
        # or branch (matches with list of know branches)
        for v in input_val[:]:
            # pick task branch if specified (has higher priority than 'branch' argument)
            if v in lut.known_branches and not branch_clause:
                branch_clause = f"AND search_string LIKE '{v}|%' "
                input_val.remove(v)
                continue
            # pick task owner nickname if specified (only first found match)
            if v.startswith("@") and not owner_clause:
                # XXX: use case insensitive 'ILIKE' here
                owner_clause = f"AND search_string ILIKE '%|{v.lstrip('@')}|%' "
                input_val.remove(v)
                continue
            # pick task state if specified (only first found match)
            if v in lut.known_states and not state_clause:
                state_clause = f"AND search LIKE '%|{v}|%' "
                input_val.remove(v)
                continue

        # handle task branch if specified and not set from 'input_val' already
        if branch and not branch_clause:
            branch_clause = f"AND search_string LIKE '{branch}|%' "

        # build WHERE clause
        where_clause += branch_clause
        where_clause += owner_clause
        where_clause2 += state_clause

        for v in input_val:
            # escape '_' symbol as it matches any symbol in SQL
            v = v.replace("_", r"\_")
            # XXX: use case insensitive 'ILIKE' here
            where_clause2 += f"AND search ILIKE '%{v}%' "

        if tasks_limit:
            limit_clause = f"LIMIT {tasks_limit}"
        else:
            limit_clause = ""

        response = self.send_sql_request(
            self.sql.task_global_search_fast.format(
                where=where_clause, where2=where_clause2, limit=limit_clause
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        tasks = []
        for el in response:
            t, task_id = el[0].split("|"), el[1]
            tasks.append(
                FastSearchTaskMeta(
                    task_id=task_id,
                    task_repo=t[0],
                    task_owner=t[1],
                    task_state=t[3],
                    components=[c for c in t[4].split(",")],
                )
            )

        res = {
            "request_args": self.args,
            "length": len(tasks),
            "tasks": [asdict(el) for el in tasks],
        }
        return res, 200


class FindTasks(APIWorker):
    """
    Tasks search lookup by id, owner or components.
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

        if self.args["input"] and len(self.args["input"]) > 4:
            self.validation_results.append(
                "input values list should contain no more than 4 elements"
            )

        if self.validation_results != []:
            return False
        return True

    def get(self):
        input_val: list[str] = self.args["input"][:] if self.args["input"] else []
        branch = self.args["branch"]
        state = tuple(self.args["state"] if self.args["state"] else [])
        owner = self.args["owner"]
        tasks_limit = self.args["tasks_limit"]

        branch_clause = ""
        owner_clause = ""
        state_clause = ""

        # filter out deleted tasks  by default
        where_clause = "WHERE type = 'task' "
        where_clause2 = "WHERE search NOT LIKE '%|DELETED|%' "

        # parse input values and look for owner name (prefixed by '@')
        # or branch (matches with list of know branches)
        for v in input_val[:]:
            # pick task branch if specified (has higher priority than 'branch' argument)
            if v in lut.known_branches and not branch_clause:
                branch_clause = f"AND search_string LIKE '{v}|%' "
                input_val.remove(v)
                continue
            # pick task owner nickname if specified (only first found match)
            if v.startswith("@") and not owner_clause:
                # XXX: use case insensitive 'ILIKE' here
                owner_clause = f"AND search_string ILIKE '%|{v.lstrip('@')}|%' "
                input_val.remove(v)
                continue
            # pick task state if specified (only first found match)
            if v in lut.known_states and not state_clause:
                state_clause = f"AND search LIKE '%|{v}|%' "
                input_val.remove(v)
                continue

        # handle task branch if specified and not set from 'input_val' already
        if branch and not branch_clause:
            branch_clause = f"AND search_string LIKE '{branch}|%' "

        # handle task owner if specified and not set from 'input_val' already
        if owner and not owner_clause:
            owner_clause = f"AND search_string ILIKE '%|{owner}|%' "

        # handle task state if specified and not set from 'input_val' already
        if state and not state_clause:
            state_clause = f"AND splitByChar('|', search)[4] IN {state} "

        # build WHERE clause
        where_clause += branch_clause
        where_clause += owner_clause
        where_clause2 += state_clause

        for v in input_val:
            # escape '_' symbol as it matches any symbol in SQL
            v = v.replace("_", r"\_")
            # XXX: use case insensitive 'ILIKE' here
            where_clause2 += f"AND search ILIKE '%{v}%' "

        if tasks_limit:
            limit_clause = f"LIMIT {tasks_limit}"
        else:
            limit_clause = ""

        response = self.send_sql_request(
            self.sql.find_tasks.format(
                where=where_clause, where2=where_clause2, limit=limit_clause
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        _tasks = {el[0]: TaskState2(*el) for el in response}

        _tmp_table = "tmp_task_ids"
        _task_ids = [{"task_id": el} for el in _tasks.keys()]

        response = self.send_sql_request(
            self.sql.get_tasks_meta.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("task_id", "UInt32"),
                    ],
                    "data": _task_ids,
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        tasks: dict[int, TaskMeta] = {}
        for el in response:
            _task = _tasks[el[0]]
            tasks[el[0]] = TaskMeta(
                task_id=_task.id,
                task_repo=_task.repo,
                task_state=_task.state,
                task_owner=_task.owner,
                task_changed=_task.ts,
                task_try=el[1],
                task_iter=el[2],
                task_message=el[3],
                task_stage=el[5],
                dependencies=el[6],
            )

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
                    "data": _task_ids,
                }
            ],
        )
        if response:
            for el in response:
                tasks[el[0]].approval.append(TaskApprovalMeta(*el[1:]))

        # get subtask info by task_id
        _tmp_table = "tmp_task_ids"
        response = self.send_sql_request(
            self.sql.get_task_subtasks.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("task_id", "UInt32"),
                    ],
                    "data": _task_ids,
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if response:
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
                            if tasks[el[0]].task_state
                            in ("BUILDING", "FAILED", "FAILING")
                        ],
                    }
                ],
            )
            if not self.sql_status:
                return self.error
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
