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

from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()

subtasks_el_model = ns.model(
    "SubTasksElementModel",
    {
        "subtask_id": fields.Integer(description="subtasks id"),
        "subtask_type": fields.String(description="subtask type"),
        "subtask_srpm": fields.String(description="subtask srpm"),
        "subtask_srpm_name": fields.String(description="source package name"),
        "subtask_srpm_evr": fields.String(
            description="source package version and release"
        ),
        "subtask_dir": fields.String(description="subtask dir"),
        "subtask_tag_id": fields.String(description="subtask tag id"),
        "subtask_tag_name": fields.String(description="subtask tag name"),
        "subtask_tag_author": fields.String(description="subtask tag author"),
        "subtask_package": fields.String(description="subtask package"),
        "subtask_pkg_from": fields.String(description="subtask package from"),
        "subtask_changed": fields.DateTime(description="subtask changed"),
        "type": fields.String(description="subtask type"),
        "stage": fields.String(description="subtask stage"),
        "stage_status": fields.String(description="stage status"),
        "status": fields.String(description="subtask status"),
        "archs": fields.List(fields.String(description="subtask architecture list")),
    },
)
task_iterations_el_model = ns.model(
    "TaskIterationsElementModel",
    {
        "task_try": fields.Integer(description="task try number"),
        "task_iter": fields.Integer(description="task iteration number"),
    },
)
last_tasks_el_model = ns.model(
    "LastTasksElementModel",
    {
        "task_id": fields.Integer(description="task id"),
        "task_repo": fields.String(description="repository name"),
        "task_state": fields.String(description="task state"),
        "task_owner": fields.String(description="task owner"),
        "task_changed": fields.DateTime(description="task changed"),
        "task_message": fields.String(description="task message"),
        "iterations": fields.Nested(
            task_iterations_el_model, description="task iteration list", as_list=True
        ),
        "subtasks": fields.Nested(
            subtasks_el_model, description="list of subtasks by task", as_list=True
        ),
    },
)
last_tasks_model = ns.model(
    "LastTaskModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of tasks found"),
        "tasks": fields.Nested(
            last_tasks_el_model,
            description="list of latest task changes",
            as_list=True,
        ),
    },
)
