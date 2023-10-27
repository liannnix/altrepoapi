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
        "is_discarded": fields.Boolean(
            description="is errata discarded", default=False
        ),
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

vuln_ids_json_post_list_model = ns.model(
    "VulnerabilitiesJsonPostListModel",
    {"vuln_ids": fields.List(fields.String, description="vulnerability ids list")},
)

vuln_model = ns.model(
    "VulnerabilityModel",
    {
        "id": fields.String(description="vulnerability id"),
        "type": fields.String(description="vulnerability type"),
        "summary": fields.String(description="vulnerability summary"),
        "score": fields.Float(description="vulnerability score"),
        "severity": fields.String(description="vulnerability severity"),
        "url": fields.String(description="vulnerability url"),
        "modified_date": fields.DateTime(description="vulnerability modified date"),
        "published_date": fields.DateTime(description="vulnerability published date"),
        "is_valid": fields.Boolean(description="vulnerability information is valid"),
        "references": fields.List(
            fields.String, description="vulnerability references list", as_list=True
        ),
        "related_vulns": fields.List(
            fields.String, description="related vulnerabilities list", as_list=True
        ),
    },
)
vuln_ids_json_list_model = ns.model(
    "VulnerabilitiesJsonListModel",
    {
        "vulns": fields.Nested(
            vuln_model,
            description="list of vulnerabilities",
            as_list=True,
        ),
        "not_found": fields.List(
            fields.String,
            description="BDUs and Bugzilla vulnerabilities not found in the DB",
        ),
    },
)

errata_manage_reference_el_model = ns.model(
    "ErrataManageReferenceElementModel",
    {
        "type": fields.String(description="errata reference type"),
        "link": fields.String(description="errata reference link"),
    },
)
errata_manage_errata_model = ns.model(
    "ErrataManageErrataModel",
    {
        "is_discarded": fields.Boolean(
            description="is errata discarded", default=False
        ),
        "id": fields.String(description="errata id"),
        "created": fields.DateTime(description="errata created date"),
        "updated": fields.DateTime(description="errata updated date"),
        "type": fields.String(description="errata type"),
        "source": fields.String(description="errata source"),
        "references": fields.Nested(
            errata_manage_reference_el_model,
            description="list of errata references",
            as_list=True,
        ),
        "pkg_hash": fields.String(description="package hash"),
        "pkg_name": fields.String(description="package name"),
        "pkg_version": fields.String(description="package version"),
        "pkg_release": fields.String(description="package release"),
        "pkgset_name": fields.String(description="packageset name"),
        "task_id": fields.Integer(description="task id"),
        "subtask_id": fields.Integer(description="subtask id"),
        "task_state": fields.String(description="task state"),
    },
)
errata_manage_errata_change_model = ns.model(
    "ErrataManageErrataChangeModel",
    {
        "id": fields.String(description="errata change id"),
        "created": fields.DateTime(description="errata created date"),
        "updated": fields.DateTime(description="errata updated date"),
        "user": fields.String(description="errata change user"),
        "user_ip": fields.String(description="errata change user IP"),
        "reason": fields.String(description="errata change reason"),
        "type": fields.String(description="errata change type"),
        "source": fields.String(description="errata change source"),
        "origin": fields.String(description="errata change origin"),
        "errata_id": fields.String(description="changed errata id refernce"),
    },
)

errata_manage_model = ns.model(
    "ErrataManageModel",
    {
        "user": fields.String(description="errata change originator"),
        "action": fields.String(description="errata manage action"),
        "reason": fields.String(description="errata change reason"),
        "errata": fields.Nested(
            errata_manage_errata_model, description="errata contents"
        ),
    },
)

errata_manage_response_model = ns.model(
    "ErrataManageResponseModel",
    {
        "message": fields.String(description="errata manage result message"),
        "action": fields.String(description="errata manage action"),
        "errata": fields.Nested(
            errata_manage_errata_model,
            description="errata contents",
            as_list=True,
        ),
        "errata_change": fields.Nested(
            errata_manage_errata_change_model,
            description="errata change contents",
            as_list=True,
        ),
    },
)

errata_manage_get_response_model = ns.model(
    "ErrataManageGetResponseModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "message": fields.String(description="errata manage result message"),
        "errata": fields.Nested(
            errata_manage_errata_model, description="errata contents"
        ),
        "vulns": fields.Nested(
            vuln_model,
            description="list of vulnerabilities closed in errata",
            as_list=True,
        ),
    },
)

errata_change_history_el_model = ns.model(
    "ErrataChangeHistoryElementModel",
    {
        "id": fields.String(description="errata change ID"),
        "errata_id": fields.String(description="errata ID"),
        "created": fields.DateTime(description="date and time the errata was created"),
        "updated": fields.DateTime(description="date and time the errata was update"),
        "user": fields.String(description="errata change user"),
        "reason": fields.String(description="errata change reason"),
        "type": fields.String(description="errata change type"),
        "source": fields.String(description="errata change source"),
        "task_id": fields.Integer(description="task id"),
        "task_state": fields.String(description="task state"),
        "vulns": fields.List(fields.String, description="errata vulnerabilities"),
        "deleted_vulns": fields.List(
            fields.String, description="deleted vulnerabilities"
        ),
        "added_vulns": fields.List(fields.String, description="added vulnerabilities"),
    },
)
errata_change_history_model = ns.model(
    "ErrataChangeHistoryModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of history found"),
        "history": fields.Nested(
            errata_change_history_el_model,
            description="errata change history",
            as_list=True,
        ),
    },
)
