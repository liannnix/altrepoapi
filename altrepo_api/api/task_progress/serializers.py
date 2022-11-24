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

subtask_archs_model = ns.model(
    "SubTaskArchitecturesModel",
    {
        "stage_status": fields.String(description="stage status"),
        "arch": fields.String(description="subtask architecture"),
    },
)
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
        "archs": fields.Nested(
            subtask_archs_model, description="list of subtask architectures"
        ),
    },
)
task_approval_el_model = ns.model(
    "TaskApprovalElementModel",
    {
        "task_id": fields.Integer(description="task id"),
        "date": fields.DateTime(description="approval date"),
        "type": fields.String(description="approval type"),
        "nickname": fields.String(description="maintainer nickname"),
        "message": fields.String(description="approval message"),
    },
)
last_tasks_el_model = ns.model(
    "LastTasksElementModel",
    {
        "task_id": fields.Integer(description="task id"),
        "task_repo": fields.String(description="repository name"),
        "task_state": fields.String(description="task state"),
        "task_owner": fields.String(description="task owner"),
        "task_try": fields.Integer(description="task try number"),
        "task_iter": fields.Integer(description="task iteration number"),
        "task_changed": fields.DateTime(description="task changed"),
        "task_message": fields.String(description="task message"),
        "task_stage": fields.String(description="task stage"),
        "dependencies": fields.List(fields.Integer, description="task dependencies"),
        "subtasks": fields.Nested(
            subtasks_el_model, description="list of subtasks by task", as_list=True
        ),
        "approval": fields.Nested(
            task_approval_el_model,
            description="list of approvals for task",
            as_list=True,
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

all_pkgsets_model = ns.model(
    "AllPackageSetsModel",
    {
        "length": fields.Integer(description="number of packagesets found"),
        "branches": fields.List(fields.String, description="list of packagesets"),
    },
)

fast_tasks_search_el_model = ns.model(
    "FastTasksSearchElementModel",
    {
        "task_id": fields.Integer(description="task id"),
        "task_owner": fields.String(description="task owner"),
        "task_state": fields.String(description="task state"),
        "task_repo": fields.String(description="repository name"),
        "components": fields.List(fields.String, description="task components"),
    },
)
fast_tasks_search_model = ns.model(
    "FastTasksSearchModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of tasks found"),
        "tasks": fields.Nested(
            fast_tasks_search_el_model,
            description="list of found tasks",
            as_list=True,
        ),
    },
)
