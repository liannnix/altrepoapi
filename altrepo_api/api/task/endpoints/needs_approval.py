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

from datetime import datetime
from typing import NamedTuple, Any

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class NeedsApproval(APIWorker):
    """
    Show tasks which need approvals by specified ACL members.
    """

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        branches = self.args["branches"]

        if branches:
            for branch in branches:
                if branch not in lut.known_approvers.keys():
                    self.validation_results.append(f"Unsupported branch: {branch}")

        if self.validation_results != []:
            return False

        return True

    def get(self):
        class SourcePackage(NamedTuple):
            name: str
            version: str
            release: str
            filename: str

        class Subtask(NamedTuple):
            source_package: SourcePackage
            id: int
            type: str
            package: str
            userid: str
            dir: str
            sid: str
            pkg_from: str
            tag_author: str
            tag_id: str
            tag_name: str
            srpm: str
            srpm_name: str
            srpm_evr: str
            last_changed: datetime

            def asdict(self) -> dict[str, Any]:
                res = self._asdict()
                res["source_package"] = self.source_package._asdict()
                return res

        class Task(NamedTuple):
            id: int
            state: str
            runby: str
            try_: int
            iter: int
            failearly: bool
            shared: bool
            depends: list[int]
            testonly: bool
            message: str
            version: str
            prev: int
            last_changed: datetime
            branch: str
            user: str
            subtasks: list[Subtask]

            def asdict(self) -> dict[str, Any]:
                res = self._asdict()
                res["subtasks"] = [s.asdict() for s in self.subtasks]
                return res

        class TaskApproval(NamedTuple):
            id: int
            repo: str
            owner: str
            changed: datetime
            subtasks: dict[int, set[str]]

        branches = self.args["branches"]
        acl_group = self.args["acl_group"]
        before_datetime = self.args["before"]

        branches = (
            set(branches) if branches is not None else set(lut.known_approvers.keys())
        )

        # (branch, group): [list of members]
        acl_map = {}
        with_p8 = "p8" in branches

        if with_p8:
            # A hack to get approvers for p8 because all its members are testers
            acl_map[("p8", "@tester")] = lut.known_approvers["p8"]

        approvers = set()
        for branch in branches:
            for approver in lut.known_approvers[branch]:
                if approver.startswith("@"):
                    approvers.add(approver)

        if approvers:
            if with_p8:
                branches.remove("p8")

            response = self.send_sql_request(
                self.sql.get_groups_memberships.format(
                    branches=tuple(branches), groups=tuple(approvers)
                )
            )
            if not self.sql_status:
                return self.error
            if not response:
                return self.store_error({"Error": "No data found in database"})

            acl_map.update(
                {(branch, group): members for group, branch, members, _ in response}
            )

            if with_p8:
                branches.add("p8")

        response = self.send_sql_request(
            self.sql.get_all_eperm_tasks_with_subtasks.format(
                branches=tuple(branches),
                datetime_clause=(
                    f"WHERE task_changed < '{before_datetime}'"
                    if before_datetime
                    else ""
                ),
            )
        )
        if not self.sql_status:
            return self.error

        task_approvals = {
            row[0]: TaskApproval(*row[:-1], {s: set() for s in row[-1]})  # type: ignore
            for row in response
        }

        # A task are approved by @maint if its owner is in @maint group
        #
        # Due to "unordinary" approval schema in p8, all it's tasks are approved
        # by @maint automatically (it's a way to generalize the algorithm of
        # this route).
        for task in task_approvals.values():
            if (
                task.owner in acl_map.get((task.repo, "@maint"), [])
                or task.repo == "p8"
            ):
                for subtask in task.subtasks.values():
                    subtask.add("@maint")

        _tmp_table = "tmp_tasks_ids"
        response = self.send_sql_request(
            self.sql.get_all_approvals_for_tasks.format(
                tmp_table=_tmp_table,
                datetime_clause=(
                    f"AND ts < '{before_datetime}'" if before_datetime else ""
                ),
            ),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("task_id", "UInt32"),
                    ],
                    "data": [{"task_id": task} for task in task_approvals],
                },
            ],
        )
        if not self.sql_status:
            return self.error

        for task_id, approvals in response:
            task = task_approvals[task_id]

            for subtask_id, app_type, app_name in approvals:
                subtask = task.subtasks.get(subtask_id)

                if subtask is None:
                    continue

                for group in ("@maint", "@tester"):
                    if app_name in acl_map.get((task.repo, group), []):
                        if app_type == "approve":
                            subtask.add(group)
                        elif app_type == "disapprove":
                            # Discard a task if it has any disapproval(-s).
                            # XXX: use `pop` method with a default value to handle
                            # repetitive deletions properly
                            _ = task_approvals.pop(task_id, None)

        def needs_approval_by_maint(X):
            # check if `@maint` group not in subtask' approvers list
            return "@maint" not in X

        def needs_approval_by_tester(X):
            # check if `@maint` group in subtask' approvers list and `@tester` is not
            return "@maint" in X and "@tester" not in X

        if acl_group == "maint":
            needs_approval_check = needs_approval_by_maint
            aggregate = any
        else:
            needs_approval_check = needs_approval_by_tester
            aggregate = all

        needs_approval: dict[int, TaskApproval] = {}

        for task in task_approvals.values():
            # XXX: all subtasks from task should be `true` with predicate function!
            # Any partially approved task are excluded from results.
            if aggregate(needs_approval_check(sub) for sub in task.subtasks.values()):
                needs_approval[task.id] = task

        _tmp_table = "tmp_tasks_ids"
        response = self.send_sql_request(
            self.sql.get_tasks_short_info.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("task_id", "UInt32"),
                        ("task_changed", "DateTime"),
                    ],
                    "data": [
                        {"task_id": task.id, "task_changed": task.changed}
                        for task in needs_approval.values()
                    ],
                },
            ],
        )
        if not self.sql_status:
            return self.error
        if len(needs_approval) != len(response):
            return self.store_error({"Error": "No data found in database"})

        result = {
            r[0]: Task(
                *r,
                branch=needs_approval[r[0]].repo,
                user=needs_approval[r[0]].owner,
                subtasks=[],
            )
            for r in response
        }

        _tmp_table = "tmp_tasks_ids"
        response = self.send_sql_request(
            self.sql.get_subtasks_short_info.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("task_id", "UInt32"),
                        ("task_changed", "DateTime"),
                    ],
                    "data": [
                        {"task_id": task.id, "task_changed": task.changed}
                        for task in needs_approval.values()
                    ],
                },
            ],
        )
        if not self.sql_status:
            return self.error
        if len(needs_approval) != len(response):
            return self.store_error({"Error": "No data found in database"})

        for task_id, subtasks in response:
            result[task_id].subtasks.extend(
                sorted(
                    (Subtask(SourcePackage(*s[:4]), *s[4:]) for s in subtasks),
                    key=lambda s: s.id,
                )
            )

        return {
            "length": len(result),
            "tasks": sorted(
                [t.asdict() | {"try": t.try_} for t in result.values()],
                key=lambda t: t["id"],
            ),
        }, 200
