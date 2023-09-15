# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

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
from typing import Any, NamedTuple

from altrepo_api.api.base import APIWorker
from altrepo_api.libs.pagination import Paginator

from .common import BDU_ID_PREFIX, CVE_ID_PREFIX, ERRATA_PACKAGE_UPDATE_PREFIX
from ..sql import sql


class SubtaskMeta(NamedTuple):
    task_id: int
    subtask_id: int
    subtask_type: str
    subtask_changed: datetime
    type: str
    src_pkg_hash: str
    src_pkg_name: str
    src_pkg_version: str
    src_pkg_release: str


@dataclass
class TaskInfo:
    task_id: int
    branch: str
    owner: str
    state: str
    changed: datetime
    erratas: list[str]
    vulnerabilities: list[dict[str, str]]
    subtasks: list[dict[str, str]] = field(default_factory=list)


class TaskList(APIWorker):
    """
    Get a list of tasks in DONE status.
    You can also search for issues by ID, task owner, component or Vulnerability.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    @staticmethod
    def _process_data_to_result(data: tuple[tuple]) -> dict[int, TaskInfo]:
        class TaskMeta(NamedTuple):
            task_id: int
            branch: str
            owner: str
            state: str
            changed: datetime
            errata_id: str
            ref_links: list[str]
            ref_types: list[str]

        result: dict[int, TaskInfo] = {}
        for el in data:
            tm = TaskMeta(*el)
            # task_id = el[0]
            if tm.task_id not in result:
                result[tm.task_id] = TaskInfo(
                    task_id=tm.task_id,
                    branch=tm.branch,
                    owner=tm.owner,
                    state=tm.state,
                    changed=tm.changed,
                    erratas=[tm.errata_id],
                    vulnerabilities=[
                        {"id": v, "type": t} for v, t in zip(tm.ref_links, tm.ref_types)
                    ],
                )
            else:
                result[tm.task_id].erratas.append(tm.errata_id)
                for v, t in zip(tm.ref_links, tm.ref_types):
                    new_vulnerability = {"id": v, "type": t}
                    if new_vulnerability not in result[tm.task_id].vulnerabilities:
                        result[tm.task_id].vulnerabilities.append(new_vulnerability)
        return result

    def get(self):
        input_val: list[str] = self.args["input"][:] if self.args["input"] else []
        branch = self.args["branch"]
        limit = self.args["limit"]
        page = self.args["page"]

        where_clause_tasks = f"AND search_string LIKE '{branch}|%' " if branch else ""
        where_clause_tasks2 = ""
        find_errata = False

        owner_clause = ""
        branch_errata_clause = f"AND pkgset_name = '{branch}'" if branch else ""
        bug_id_clause = ""

        errata_conditions = []

        # parse input values and look for owner name (prefixed by '@'),
        # errata ID (prefixed by 'ALT-PU') or
        # vulnerability (prefixed by 'CVE-' or 'BDU:')
        for v in input_val[:]:
            # pick task owner nickname if specified (only first found match)
            if v.startswith("@") and not owner_clause:
                # XXX: use case insensitive 'ILIKE' here
                owner_clause = f"AND search_string ILIKE '%|{v.lstrip('@')}|%' "
                input_val.remove(v)
                continue

            v_up = v.upper()
            # pick errata ID if specified
            if v_up.startswith(ERRATA_PACKAGE_UPDATE_PREFIX):
                errata_conditions.append(f"(errata_id LIKE '{v_up}%')")
                input_val.remove(v)
                find_errata = True
                continue

            # pick vulnerability ID if specified (CVE or BDU)
            if v_up.startswith(CVE_ID_PREFIX) or v_up.startswith(BDU_ID_PREFIX):
                errata_conditions.append(
                    f"arrayExists(x -> x LIKE '{v_up}%', refs_links)"
                )
                input_val.remove(v)
                find_errata = True
                continue

            # pick bug ID in the vulnerabilities
            if v.startswith("bug:"):
                bug_id_clause = (
                    f"arrayExists(x -> x LIKE " f"'{v.lstrip('bug:')}%', refs_links)"
                )
                find_errata = True
                input_val.remove(v)
                continue

        if errata_conditions:
            condition = f"WHERE {' AND '.join(errata_conditions)}"
            condition += f" OR {bug_id_clause}" if bug_id_clause else ""
        else:
            condition = f"WHERE {bug_id_clause}" if bug_id_clause else ""

        where_clause_errata = (
            f"WHERE task_id IN (SELECT task_id FROM errata_tasks {condition})"
            if condition
            else ""
        )

        if find_errata is True:
            where_clause_errata += (
                "AND errata_id != ''"
                if where_clause_errata
                else "WHERE errata_id != ''"
            )

        for v in input_val:
            # escape '_' symbol as it matches any symbol in SQL
            v = v.replace("_", r"\_")
            if v.startswith("#"):
                v = v.lstrip("#")
            where_clause_tasks2 += f"AND search ILIKE '%{v}%' "

        response = self.send_sql_request(
            self.sql.get_task_list.format(
                branch_errata_clause=branch_errata_clause,
                where_clause_errata=where_clause_errata,
                where_clause_tasks=where_clause_tasks + owner_clause,
                where_clause_tasks2=where_clause_tasks2,
            ),
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No data not found in database"})

        _tasks = self._process_data_to_result(response)

        paginator = Paginator(list(_tasks.values()), limit)
        page_obj = paginator.get_page(page)

        # get subtasks info by task_id
        _tmp_table = "tmp_task_id"
        response = self.send_sql_request(
            self.sql.get_subtasks.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [("task_id", "UInt32"), ("changed", "DateTime")],
                    "data": [
                        {"task_id": el.task_id, "changed": el.changed}
                        for el in page_obj
                    ],
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if response:
            for task in page_obj:
                for el in response:
                    if task.task_id == el[0]:
                        task.subtasks.append(SubtaskMeta(*el)._asdict())

        res: dict[str, Any] = {
            "request_args": self.args,
            "length": paginator.limit,
            "tasks": [asdict(el) for el in page_obj],
        }

        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )
