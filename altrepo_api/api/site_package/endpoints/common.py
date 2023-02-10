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
class PackageInfo(Protocol):
    name: str
    version: str
    release: str
    arch: str
    epoch: int
    buildtime: int
    url: str
    license: str
    summary: str
    description: str
    packager: str
    packager_nickname: str
    category: str


class _pAPIWorker(Protocol):
    sql: SQL
    sql_status: bool

    def store_error(
        self, message: dict[str, Any], severity: int = ..., http_code: int = ...
    ):
        ...

    def send_sql_request(
        self, request_line: Any, http_code: int = ..., **kwargs
    ) -> Any:
        ...


class _pLUT(Protocol):
    gitalt_base: str


class _pHasLUT(Protocol):
    lut: _pLUT


class _pHasPackeInfo(Protocol):
    pkg_info: PackageInfo


class _pHasBranchHashAndSrcFlag(Protocol):
    branch: str
    is_src: int
    pkghash: int


class _pParseTaskGearMixin(_pHasLUT, _pHasPackeInfo, Protocol):
    pass


class _pFindBuildSubtaskMixin(_pHasBranchHashAndSrcFlag, _pAPIWorker, Protocol):
    def _get_build_tasks(self) -> tuple[list[BuildTask], list[SubtaskInfo]]:
        ...


class _pFindBuildTaskMixixn(_pFindBuildSubtaskMixin, Protocol):
    def find_build_subtask(self) -> Union[SubtaskInfo, None]:
        ...

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
        ]  # 'Any' here is a hack to fix type checking errors
    ) -> Union[SubtaskInfo, None]:
        pkg_task = 0

        def _get_first_by_id(task_id, subtasks: list[SubtaskInfo]):
            for sub in subtasks:
                if sub.task_id == task_id:
                    yield sub
                    break

        # get package build tasks by hash
        try:
            build_tasks, build_subtasks = self._get_build_tasks()
        except SQLRequestError:
            raise

        for t in build_tasks:
            if t.branch == self.branch:
                pkg_task = t.task_id
                break

        if pkg_task:
            # we've found build task in given brunch
            for sub in _get_first_by_id(pkg_task, build_subtasks):
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
        ]  # 'Any' here is a hack to fix type checking errors
    ) -> tuple[int, int, str, str, list[dict[str, Any]]]:
        pkg_task = 0
        pkg_tasks = []
        pkg_subtask = 0
        pkg_task_date = ""
        gear_link = ""

        sub = self.find_build_subtask()
        if sub is None:
            return pkg_task, pkg_subtask, pkg_task_date, gear_link, pkg_tasks

        pkg_task = sub.task_id
        pkg_subtask = sub.subtask_id
        pkg_task_date = datetime_to_iso(sub.task_changed)

        if pkg_task:
            # we've found build task in given brunch
            if sub.type != "copy":
                gear_link = self._parse_task_gear(sub)
                type_ = "build"
            else:
                type_ = "copy"
            pkg_tasks.append({"type": type_, "id": pkg_task, "date": pkg_task_date})
        else:
            # no build task found in given brunch, use one from another branch
            if sub.type != "copy":
                gear_link = self._parse_task_gear(sub)
                pkg_tasks.append(
                    {"type": "build", "id": pkg_task, "date": pkg_task_date}
                )

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
