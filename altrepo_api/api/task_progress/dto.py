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
import datetime
from dataclasses import dataclass, field
from typing import NamedTuple


@dataclass(frozen=True, order=True)
class IterationMeta:
    task_try: int
    task_iter: int


@dataclass
class TaskApprovalMeta:
    type: str
    nickname: str
    message: str = ""


@dataclass
class SubtaskArchsMeta:
    arch: str
    stage_status: str


@dataclass
class SubtaskMeta:
    task_id: int
    subtask_id: int
    subtask_type: str
    subtask_srpm: str
    subtask_srpm_name: str
    subtask_srpm_evr: str
    subtask_dir: str
    subtask_tag_id: str
    subtask_tag_name: str
    subtask_tag_author: str
    subtask_package: str
    subtask_pkg_from: str
    subtask_changed: datetime.datetime
    type: str
    archs: list[SubtaskArchsMeta] = field(default_factory=list)
    approval: list[TaskApprovalMeta] = field(default_factory=list)


@dataclass
class TaskMeta:
    task_id: int
    task_repo: str
    task_state: str
    task_owner: str
    task_try: int
    task_iter: int
    task_testonly: int
    task_changed: datetime.datetime
    task_message: str
    task_stage: str
    dependencies: list[int] = field(default_factory=list)
    iterations: list[IterationMeta] = field(default_factory=list)
    subtasks: list[SubtaskMeta] = field(default_factory=list)
    approval: list[TaskApprovalMeta] = field(default_factory=list)


@dataclass
class FastSearchTaskMeta:
    task_id: int
    task_owner: str
    task_repo: str
    task_state: str
    components: list[str]


class TaskState(NamedTuple):
    table: str
    id: int
    state: str
    changed: datetime.datetime


class TaskState2(NamedTuple):
    id: int
    repo: str
    owner: str
    state: str
    ts: datetime.datetime
