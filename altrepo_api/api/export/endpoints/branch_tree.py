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

from datetime import datetime, timezone
from typing import Any, NamedTuple

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


class BranchPoint(NamedTuple):
    branch: str
    task: Task
    from_task: Task

    def asdict(self) -> dict[str, Any]:
        return {
            "branch": self.branch,
            "task": self.task.asdict(),
            "from_task": self.from_task.asdict(),
        }


class BranchTreeExport(APIWorker):
    """Retrieves branch history tree."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        # get 'DONE' tasks history
        response = self.send_sql_request(
            self.sql.get_done_tasks.format(branches=lut.branch_tree_branches)
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
            self.sql.get_branch_history.format(branches=lut.branch_tree_branches)
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

        # find branch points
        branch_points: list[BranchPoint] = []
        for task in tasks.values():
            # skip branch history breaks
            task_prev = tasks.get(task.prev)
            if task_prev is None:
                continue

            if task.branch != task_prev.branch:
                branch_points.append(
                    BranchPoint(branch=task.branch, task=task, from_task=task_prev)
                )

        res = {
            "branches": lut.branch_tree_branches,
            "tasks": [t.asdict() for t in tasks.values()],
            "branch_commits": [bc.asdict() for bc in branch_commits],
            "branch_points": [bp.asdict() for bp in branch_points],
        }

        last_modified = datetime.strftime(
            next(iter(tasks.values())).date.astimezone(timezone.utc),
            "%a, %d %b %Y %H:%M:%S",
        )

        return res, 200, {"Last-Modified": f"{last_modified} GMT"}
