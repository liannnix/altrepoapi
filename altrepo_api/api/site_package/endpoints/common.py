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

from datetime import datetime
from typing import Any, NamedTuple, Protocol, Union

from altrepo_api.utils import datetime_to_iso

from ..sql import SQL


# custom exceptions
class SQLRequestError(Exception):
    def __init__(self, message="", error=None):
        super().__init__(message)
        self.error = error


class NoDataFoundInDB(Exception):
    pass


# DTOs
class BuildTask(NamedTuple):
    branch: str
    task_id: int
    task_changed: datetime


class SubtaskInfo(NamedTuple):
    branch: str
    task_id: int
    subtask_id: int
    type: str
    dir: str
    tag_id: str
    srpm_name: str
    srpm_evr: str
    task_changed: datetime


# Protocols
class _pAPIWorker(Protocol):
    sql: SQL
    sql_status: bool

    def store_error(
        self, message: dict[str, Any], severity: int = ..., http_code: int = ...
    ) -> tuple[Any, int]:
        ...

    def send_sql_request(
        self, request_line: Any, http_code: int = ..., **kwargs
    ) -> Any:
        ...


class _pPackageInfo(Protocol):
    name: str


class _pLUT(Protocol):
    gitalt_base: str


class _pHasLUT(Protocol):
    lut: _pLUT


class _pHasPackageInfo(Protocol):
    pkg_info: _pPackageInfo


class _pHasBranchHashAndSrcFlag(Protocol):
    branch: str
    is_src: int
    pkghash: int


class _pParseTaskGearMixin(_pHasLUT, _pHasPackageInfo, Protocol):
    pass


class _pFindBuildSubtaskMixin(_pHasBranchHashAndSrcFlag, _pAPIWorker, Protocol):
    def _get_build_tasks(self) -> tuple[list[BuildTask], list[SubtaskInfo]]:
        ...


class _pFindBuildTaskMixixn(_pFindBuildSubtaskMixin, Protocol):
    def _parse_task_gear(self, subtask: SubtaskInfo) -> str:
        ...


class ParseTaskGearMixin:
    def _parse_task_gear(self: _pParseTaskGearMixin, subtask: SubtaskInfo) -> str:
        return parse_task_gear(self.pkg_info.name, subtask, self.lut.gitalt_base)


class FindBuildSubtaskMixin:
    def _get_build_tasks(
        self: _pFindBuildSubtaskMixin,
    ) -> tuple[list[BuildTask], list[SubtaskInfo]]:
        tasks = []
        subtasks = []

        response = self.send_sql_request(
            self.sql.get_package_build_tasks.format(
                pkghash=self.pkghash, source=self.is_src
            )
        )
        if not self.sql_status:
            raise SQLRequestError

        if response:
            tasks = sorted(
                [BuildTask(*el) for el in response],
                key=lambda x: x.task_changed,
                reverse=True,
            )
        else:
            return tasks, subtasks

        response = self.send_sql_request(
            self.sql.get_gears_from_tasks.format(
                pkghash=self.pkghash,
                tasks=tuple((t.task_id, str(t.task_changed)) for t in tasks),
            )
        )
        if not self.sql_status:
            raise SQLRequestError

        if response:
            subtasks = [SubtaskInfo(*el) for el in response]

        return tasks, subtasks

    def find_build_subtask(
        self: Union[
            _pFindBuildSubtaskMixin, Any
        ]  # XXX: 'Any' here is a hack to fix type checking errors
    ) -> Union[SubtaskInfo, None]:
        pkg_task = 0

        # get package build tasks by hash
        build_tasks, build_subtasks = self._get_build_tasks()

        # find task from current branch if any
        for t in build_tasks:
            if t.branch == self.branch:
                pkg_task = t.task_id
                break

        if pkg_task:
            # we've found build task in given brunch
            for sub in build_subtasks:
                if sub.task_id == pkg_task:
                    return sub
        else:
            # no build task found in given brunch, so try to find one from another branch
            for sub in build_subtasks:
                if sub.type != "copy":
                    return sub

        return None


class FindBuildTaskMixixn(FindBuildSubtaskMixin, ParseTaskGearMixin):
    def find_and_parse_build_task(
        self: Union[
            _pFindBuildTaskMixixn, Any
        ]  # XXX: 'Any' here is a hack to fix type checking errors
    ) -> tuple[int, int, str, str, list[dict[str, Any]]]:
        pkg_task = 0
        pkg_tasks = []
        pkg_subtask = 0
        pkg_task_date = ""
        gear_link = ""

        tasks, subtasks = self._get_build_tasks()

        if not tasks or not subtasks:
            return pkg_task, pkg_subtask, pkg_task_date, gear_link, pkg_tasks

        subs = {s.task_id: s for s in subtasks}

        # filter out build tasks from other branches with same source package hash (closes #45195)
        branch_tasks = list(filter(lambda x: x.branch == self.branch, tasks))
        if branch_tasks and subs[branch_tasks[0].task_id].type != "copy":
            sub = subs[branch_tasks[0].task_id]
            pkg_task = sub.task_id
            pkg_subtask = sub.subtask_id
            pkg_task_date = datetime_to_iso(sub.task_changed)
            gear_link = self._parse_task_gear(sub)
            pkg_tasks.append({"type": "build", "id": pkg_task, "date": pkg_task_date})
            return pkg_task, pkg_subtask, pkg_task_date, gear_link, pkg_tasks

        for task in tasks:
            sub = subs[task.task_id]
            if sub.branch == self.branch:
                # we've found build task in given brunch
                pkg_task = sub.task_id
                pkg_subtask = sub.subtask_id
                pkg_task_date = datetime_to_iso(sub.task_changed)
                if sub.type != "copy":
                    gear_link = self._parse_task_gear(sub)
                    pkg_tasks.append(
                        {"type": "build", "id": pkg_task, "date": pkg_task_date}
                    )
                    break
                else:
                    pkg_tasks.append(
                        {"type": "copy", "id": pkg_task, "date": pkg_task_date}
                    )
            else:
                # no build task found in given brunch, use one from another branch
                if sub.type != "copy":
                    pkg_task = sub.task_id
                    pkg_subtask = sub.subtask_id
                    pkg_task_date = datetime_to_iso(sub.task_changed)
                    gear_link = self._parse_task_gear(sub)
                    pkg_tasks.append(
                        {"type": "build", "id": pkg_task, "date": pkg_task_date}
                    )
                    break

        return pkg_task, pkg_subtask, pkg_task_date, gear_link, pkg_tasks


def parse_task_gear(pkgname: str, subtask: SubtaskInfo, git_base_url: str) -> str:
    """Builds link to Git repository based on information from subtask."""

    def delete_epoch(evr: str) -> str:
        if ":" in evr:
            return evr.split(":")[-1]
        return evr

    if subtask.type == "copy":
        # 'copy' always has only 'subtask_package'
        return pkgname

    if subtask.type == "delete" and subtask.srpm_name != "":
        # XXX: bug workaround for girar changes @ e74d8067009d
        link = f"{git_base_url}/srpms/{pkgname[0]}/{pkgname}.git"
        if subtask.srpm_evr != "":
            link += f"?a=tree;hb={delete_epoch(subtask.srpm_evr)}"
        return link

    if subtask.type == "delete":
        # 'delete' return only package name
        return pkgname

    if subtask.dir != "" or subtask.type == "gear":
        # 'gear' and 'rebuild' + 'unknown' with gears
        link = f"{git_base_url}/gears/{pkgname[0]}/{pkgname}.git"
        if subtask.tag_id != "":
            link += f"?a=tree;hb={subtask.tag_id}"
        return link

    if subtask.srpm_name != "" or subtask.type == "srpm":
        # 'srpm' and 'rebuild' + 'unknown' with srpm
        link = f"{git_base_url}/srpms/{pkgname[0]}/{pkgname}.git"
        if subtask.srpm_evr != "":
            link += f"?a=tree;hb={delete_epoch(subtask.srpm_evr)}"
        return link

    return ""
