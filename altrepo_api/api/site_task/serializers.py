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

task_by_name_pkg_model = ns.model(
    "SiteTaskByNamePackageModel",
    {
        "type": fields.String(description="subtask type [gear|srpm|delete|search]"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "link": fields.String(description="package git link"),
    },
)
task_by_name_task_model = ns.model(
    "SiteTaskByNameTaskModel",
    {
        "id": fields.Integer(description="task id"),
        "state": fields.String(description="task state"),
        "branch": fields.String(description="task branch"),
        "owner": fields.String(description="task owner nickname"),
        "changed": fields.String(description="task last changed (ISO 8601 format)"),
        "packages": fields.Nested(
            task_by_name_pkg_model, description="task packages", as_list=True
        ),
    },
)
task_by_name_model = ns.model(
    "SiteTaskByNameModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of tasks found"),
        "tasks": fields.Nested(
            task_by_name_task_model, description="tasks list", as_list=True
        ),
    },
)


last_packages_el_model = ns.model(
    "SiteLastPackagesElementModel",
    {
        "subtask_id": fields.Integer(description="subtask id"),
        "subtask_userid": fields.String(description="subtask created by"),
        "subtask_type": fields.String(
            description="subtask type [build|rebuild|delete]"
        ),
        "hash": fields.String(
            attribute="pkg_hash", description="package hash UInt64 as string"
        ),
        "name": fields.String(attribute="pkg_name", description="package name"),
        "version": fields.String(
            attribute="pkg_version", description="package version"
        ),
        "release": fields.String(
            attribute="pkg_release", description="package release"
        ),
        "summary": fields.String(
            attribute="pkg_summary", description="package summary"
        ),
        "buildtime": fields.Integer(
            attribute="pkg_buildtime", description="package buildtime"
        ),
        "changelog_name": fields.String(description="package last changelog name"),
        "changelog_nickname": fields.String(
            description="package last changelog nickname"
        ),
        "changelog_date": fields.String(
            description="package last changelog message date"
        ),
        "changelog_text": fields.String(description="package last changelog message"),
    },
)
last_packages_pkg_model = ns.model(
    "SiteLastPackagesPackageModel",
    {
        "task_id": fields.Integer(description="task id"),
        "task_owner": fields.String(description="task owner"),
        "task_changed": fields.String(description="task completed at"),
        "task_message": fields.String(description="task message"),
        "packages": fields.Nested(
            last_packages_el_model,
            description="task subtasks packages information",
            as_list=True,
        ),
    },
)
last_packages_model = ns.model(
    "SiteLastPackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "tasks": fields.Nested(
            last_packages_pkg_model,
            description="last tasks packages information",
            as_list=True,
        ),
        "last_branch_task": fields.Integer(description="last loaded branch task"),
        "last_branch_date": fields.String(description="last loaded branch date"),
    },
)

pkgs_versions_from_tasks_el_model = ns.model(
    "SItePackagesVersionsFromTasksElementModel",
    {
        "branch": fields.String(description="package set name"),
        "task": fields.Integer(description="package build task"),
        "hash": fields.String(description="package hash UInt64 as string"),
        "owner": fields.String(description="task owner nickname"),
        "changed": fields.DateTime(description="task change date"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
    },
)
pkgs_versions_from_tasks_model = ns.model(
    "SItePackagesVersionsFromTasksModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of versions found"),
        "versions": fields.Nested(
            pkgs_versions_from_tasks_el_model,
            description="package versions list",
            as_list=True,
        ),
    },
)
