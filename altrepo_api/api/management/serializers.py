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

from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()

vulns_el_model = ns.model(
    "VulnerabilitiesElementModel",
    {
        "id": fields.String(description="vulnerability id"),
        "type": fields.String(description="vulnerability type"),
    },
)
subtask_info_el_model = ns.model(
    "SubTaskInfoElementModel",
    {
        "subtask_id": fields.Integer(description="subtasks id"),
        "subtask_type": fields.String(description="subtask type"),
        "subtask_changed": fields.DateTime(description="subtask changed"),
        "type": fields.String(description="subtask type"),
        "src_pkg_name": fields.String(description="source package name"),
        "src_pkg_hash": fields.String(description="source package hash"),
        "src_pkg_version": fields.String(description="source package version"),
        "src_pkg_release": fields.String(description="source package release"),
    },
)
task_list_el_model = ns.model(
    "TaskListElementModel",
    {
        "task_id": fields.Integer(description="task id"),
        "branch": fields.String(description="repository name"),
        "owner": fields.String(description="task owner"),
        "state": fields.String(description="task state"),
        "changed": fields.DateTime(description="task changed"),
        "erratas": fields.List(fields.String, description="errata ID list"),
        "vulnerabilities": fields.Nested(
            vulns_el_model,
            description="fixed vulnerabilities list",
            as_list=True,
        ),
        "subtasks": fields.Nested(
            subtask_info_el_model, description="list of subtasks by task", as_list=True
        ),
    },
)
task_list_model = ns.model(
    "TasksListModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of tasks found"),
        "tasks": fields.Nested(
            task_list_el_model,
            description="list of task",
            as_list=True,
        ),
    },
)

subtask_errata_el_model = ns.model(
    "SubtaskErrataElementModel",
    {
        "subtask_id": fields.Integer(description="subtask ID"),
        "subtask_changed": fields.DateTime(
            description="date and time the subtask was last changed"
        ),
        "src_pkg_hash": fields.String(description="package hash UInt64 as string"),
        "src_pkg_name": fields.String(description="source package name"),
        "src_pkg_version": fields.String(description="source package version"),
        "src_pkg_release": fields.String(description="source package release"),
        "chlog_text": fields.String(description="package last changelog message"),
        "chlog_date": fields.DateTime(
            description="package last changelog message date"
        ),
        "chlog_name": fields.String(description="package last changelog name"),
        "chlog_evr": fields.String(description="package last changelog evr"),
        "errata_id": fields.String(description="errata ID"),
        "eh_created": fields.DateTime(
            description="date and time the errata was created"
        ),
        "eh_update": fields.DateTime(description="date and time the errata was update"),
        "vulnerabilities": fields.Nested(
            vulns_el_model, description="fixed vulnerabilities list", as_list=True
        ),
    },
)
task_info_model = ns.model(
    "TaskInfoModel",
    {
        "task_id": fields.Integer(description="task id"),
        "task_repo": fields.String(description="repository where the task was built"),
        "task_state": fields.String(description="task state"),
        "task_changed": fields.DateTime(
            description="date and time the task was last changed"
        ),
        "task_message": fields.String(description="task message"),
        "task_owner": fields.String(description="task owner nickname"),
        "subtasks": fields.Nested(
            subtask_errata_el_model,
            description="list of subtasks and vulnerabilities by task ID",
            as_list=True,
        ),
    },
)
