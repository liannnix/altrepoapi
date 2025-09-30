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

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import NamedTuple, Optional

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.api.metadata import KnownFilterTypes, MetadataChoiceItem, MetadataItem
from altrepo_api.utils import make_tmp_table_name
from altrepo_api.api.misc import lut

from .tools.constants import (
    BDU_ID_PREFIX,
    CVE_ID_PREFIX,
    ERRATA_PACKAGE_UPDATE_PREFIX,
    GHSA_ID_PREFIX,
)
from ..parsers import task_list_args
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


class TaskListArgs(NamedTuple):
    state: str
    is_errata: bool
    input: Optional[list[str]] = None
    branch: Optional[str] = None
    page: Optional[int] = None
    limit: Optional[int] = None


@dataclass
class ParsedInput:
    vulns: list[str] = field(default_factory=list)
    bugs: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    erratas: list[str] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)


class TaskList(APIWorker):
    """
    Get a list of tasks.
    You can also search for issues by ID, task owner, component or Vulnerability.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.kwargs = kwargs
        self.args: TaskListArgs
        self.input_values: ParsedInput
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.args = TaskListArgs(**self.kwargs)
        self.input = self._parse_input(self.args.input or [])
        self.logger.debug(f"args : {self.kwargs}")
        return True

    def _parse_input(self, input_values: list[str]) -> ParsedInput:
        BUG_PREFIX = "BUG:"
        TASK_PREFIX = "#"
        OWNER_PREFIX = "@"

        parsed = ParsedInput()
        for value in input_values:
            v = value.strip().upper()

            if (
                v.startswith(CVE_ID_PREFIX)
                or v.startswith(BDU_ID_PREFIX)
                or v.startswith(GHSA_ID_PREFIX)
            ):
                parsed.vulns.append(v)
            elif v.startswith(BUG_PREFIX):
                parsed.bugs.append(v.removeprefix(BUG_PREFIX))
            elif v.startswith(TASK_PREFIX):
                parsed.tasks.append(v.removeprefix(TASK_PREFIX))
            elif v.startswith(ERRATA_PACKAGE_UPDATE_PREFIX):
                parsed.erratas.append(v)
            elif v.startswith(OWNER_PREFIX):
                parsed.owners.append(v.removeprefix(OWNER_PREFIX))

        return parsed

    @property
    def _limit(self) -> str:
        return f"LIMIT {self.args.limit}" if self.args.limit else ""

    @property
    def _page(self) -> str:
        if self.args.limit and self.args.page:
            page = self.args.page
            per_page = self.args.limit
            offset = (page - 1) * per_page
            return f"OFFSET {offset}"
        return ""

    @property
    def _where_clause_errata(self) -> str:
        errata_conditions = []

        for v in self.input.erratas:
            errata_conditions.append(f"(errata_id LIKE '{v}%')")
        for v in self.input.vulns:
            errata_conditions.append(f"arrayExists(x -> x LIKE '{v}%', refs_links)")
        for v in self.input.bugs:
            errata_conditions.append(f"arrayExists(x -> x LIKE '{v}%', refs_links)")

        condition = ""
        if errata_conditions:
            condition = "WHERE (" + " AND ".join(errata_conditions) + ")"

        where_clause_errata = (
            f"WHERE task_id IN (SELECT task_id FROM errata_tasks {condition})"
            if condition
            else ""
        )

        if errata_conditions:
            where_clause_errata += (
                " AND errata_id != ''"
                if where_clause_errata
                else "WHERE errata_id != ''"
            )

        return where_clause_errata

    @property
    def _where_clause_tasks2(self) -> str:
        where_clause_tasks2 = ""
        if self.input.tasks:
            where_clause_tasks2 = (
                " AND ("
                + " OR ".join(f"search ILIKE '%{v}%'" for v in self.input.tasks)
                + ")"
            )
        return where_clause_tasks2

    @property
    def _where_clause_is_errata(self) -> str:
        return "WHERE errata != ''" if self.args.is_errata else ""

    @property
    def _branch_errata_clause(self) -> str:
        return f"AND pkgset_name = '{self.args.branch}'" if self.args.branch else ""

    @property
    def _where_clause_tasks(self) -> str:
        return (
            f"AND search_string LIKE '{self.args.branch}|%' "
            if self.args.branch
            else ""
        )

    @property
    def _state_clause(self) -> str:
        return (
            "(search LIKE '%|DONE|%' OR search LIKE '%|TESTED|%' OR search LIKE '%|EPERM|%')"
            if self.args.state == "all"
            else f"search LIKE '%|{self.args.state}|%'"
        )

    @property
    def _state_clause2(self) -> list[str]:
        return (
            ["DONE", "TESTED", "EPERM"]
            if self.args.state == "all"
            else [self.args.state]
        )

    @property
    def _owner_clause(self) -> str:
        owner_clause = ""
        if self.input.owners:
            owner_clause = (
                " AND ("
                + " OR ".join(
                    f"search_string ILIKE '%|{v}|%' " for v in self.input.owners
                )
                + ")"
            )
        return owner_clause

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
            tm = TaskMeta(*el[:-1])
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
        response = self.send_sql_request(
            self.sql.get_task_list.format(
                branch_errata_clause=self._branch_errata_clause,
                state_clause=self._state_clause,
                state_clause2=self._state_clause2,
                where_clause_errata=self._where_clause_errata,
                where_clause_tasks=self._where_clause_tasks + self._owner_clause,
                where_clause_tasks2=self._where_clause_tasks2,
                where_clause_is_errata=self._where_clause_is_errata,
                limit=self._limit,
                page=self._page,
            ),
        )

        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No data not found in database"})

        total_count = response[0][-1]

        tasks = self._process_data_to_result(response).values()

        # get subtasks info by task_id
        _tmp_table = make_tmp_table_name("tmp_task_id")
        # XXX: handle 'EPERM' tasks in specific way due to 'ts' field from GlobalSearch
        # table is inconsistent with 'task_changed' field of TaskIterations table
        response = self.send_sql_request(
            self.sql.get_subtasks.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("task_id", "UInt32"),
                        ("changed", "DateTime"),
                        ("state", "String"),
                    ],
                    "data": [
                        {
                            "task_id": el.task_id,
                            "changed": el.changed,
                            "state": el.state,
                        }
                        for el in tasks
                    ],
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if response:
            for task in tasks:
                for el in response:
                    if task.task_id == el[0]:
                        task.subtasks.append(SubtaskMeta(*el)._asdict())

        return (
            {
                "request_args": self.args._asdict(),
                "length": len(tasks),
                "tasks": [asdict(el) for el in tasks],
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": total_count,
            },
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for arg in task_list_args.args:
            item_info = {
                "name": arg.name,
                "label": arg.name.replace("_", " ").capitalize(),
                "help_text": arg.help,
            }
            if arg.name == "branch":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(value=branch, display_name=branch)
                            for branch in lut.errata_manage_branches_with_tasks
                        ],
                    )
                )

            if arg.name == "state":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(
                                value=choice, display_name=choice.capitalize()
                            )
                            for choice in arg.choices
                            if choice != "all"
                        ],
                    )
                )

            if arg.name == "is_errata":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(value="true", display_name="True"),
                            MetadataChoiceItem(value="false", display_name="False"),
                        ],
                    )
                )

        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200
