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

from datetime import datetime, timezone
from typing import Any, NamedTuple, Union

from altrepo_api.utils import sort_branches

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class Task(NamedTuple):
    id: int
    prev: int
    branch: str
    date: datetime

    def asdict(self) -> dict[str, Any]:
        return self._asdict()


class BranchCommit(NamedTuple):
    name: str
    date: datetime
    task: int

    def asdict(self) -> dict[str, Any]:
        return self._asdict()


class TasksHistoryArgs(NamedTuple):
    task_id: Union[str, None]


class TasksHistory(APIWorker):
    """Retrieves all done tasks for all branches"""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = TasksHistoryArgs(**kwargs)
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.logger.debug(f"args : {self.args}")
        task_id = self.args.task_id
        if task_id:
            response = self.send_sql_request(
                self.sql.get_count_task_id.format(task_id=self.args.task_id)
            )
            return response[0][0] > 0
        return True

    @property
    def _where_clause(self) -> str:
        where_clause = (
            f"AND task_id  = {self.args.task_id}" if self.args.task_id else ""
        )

        return where_clause

    def get(self):
        # get active branches
        response = self.send_sql_request(self.sql.get_active_pkgsets)
        if not self.sql_status:
            return self.error
        if not response:
            _branches = sort_branches(lut.known_branches)
        else:
            _branches = sort_branches(el[0] for el in response)

        active_branches = [
            branch
            for branch in _branches
            if not any(
                keyword in branch for keyword in ["_e2k", "_riscv64", "_loongarch64"]
            )
        ]
        # get done tasks
        response = self.send_sql_request(
            self.sql.get_done_tasks.format(
                branches=active_branches,
                where_clause=self._where_clause,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data found in DB", "args": self.args}
            )

        tasks = {t.id: t for t in (Task(*el) for el in response)}

        # get branch commit history
        response = self.send_sql_request(
            self.sql.get_branch_history.format(branches=active_branches)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data found in DB", "args": self.args}
            )

        branch_commits = [
            b for b in (BranchCommit(*el) for el in response) if b.task in tasks
        ]

        res = {
            "branches": active_branches,
            "tasks": [t.asdict() for t in tasks.values()],
            "branch_commits": [bc.asdict() for bc in branch_commits],
        }

        last_modified = datetime.strftime(
            next(iter(tasks.values())).date.astimezone(timezone.utc),
            "%a, %d %b %Y %H:%M:%S",
        )

        return res, 200, {"Last-Modified": f"{last_modified} GMT"}
