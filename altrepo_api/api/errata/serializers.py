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

oval_branches_model = ns.model(
    "OvalBranchesModel",
    {
        "length": fields.Integer(description="number of branches"),
        "branches": fields.List(fields.String, description="OVAL export available branches"),
    },
)

errata_json_list_model = ns.model(
    "ErrataJsonPostListModel",
    {
        "errata_ids": fields.List(fields.String, description="errata ids list")
    },
)
errata_reference_model = ns.model(
    "ErrataReferenceModel",
    {
        "id": fields.String(description="errata id"),
        "type": fields.String(description="errata type"),
        "link": fields.String(descriptin="errata link"),
    }
)
errata_model = ns.model(
    "ErrataModel",
    {
        "id": fields.String(description="errata id"),
        "type": fields.String(description="errata type"),
        "pkgset_name": fields.String(description="packageset name"),
        "pkgset_date": fields.Date(description="packageset date"),
        "task_id": fields.Integer(description="task id"),
        "task_state": fields.String(description="task state"),
        "task_changed": fields.String(description="task changed date"),
        "subtask_id": fields.Integer(description="subtask id"),
        "pkg_hash": fields.String(description="package hash"),
        "pkg_name": fields.String(description="package name"),
        "pkg_version": fields.String(description="package version"),
        "pkg_release": fields.String(description="package release"),
        "references": fields.Nested(
            errata_reference_model,
            description="list of references",
            as_list=True,
        ),
    }
)
errata_search_model = ns.model(
    "ErrataSearchModel",
    {
        "erratas": fields.Nested(errata_model, description="list of erratas", as_list=True)
    },
)

errata_bug_model = ns.model(
    "ErrataBugModel",
    {
        "id": fields.Integer(description="bug id"),
        "status": fields.String(description="bug status"),
        "resolution": fields.String(description="bug resolution"),
        "severity": fields.String(description="bug severity"),
        "priority": fields.String(description="bug priority"),
        "product": fields.String(description="bug product"),
        "version": fields.String(description="bug version"),
        "platform": fields.String(description="bug platform"),
        "component": fields.String(description="bug component"),
        "assignee": fields.String(description="bug assignee"),
        "reporter": fields.String(description="bug reporter"),
        "summary": fields.String(description="bug summary"),
        "last_changed": fields.String(description="bug last changed date"),
        "assignee_full": fields.String(description="bug assignee (full)"),
        "reporter_full": fields.String(description="bug reporter (full)")
    }
)
errata_vuln_model = ns.model(
    "ErrataVulnModel",
    {
        "id": fields.String(description="vulnerability id"),
        "hash": fields.String(description="vulnerability hash"),
        "type": fields.String(description="vulnerability type"),
        "summary": fields.String(description="vulnerability summary"),
        "score": fields.Float(description="vulnerability score"),
        "severity": fields.String(description="vulnerability severity"),
        "url": fields.String(description="vulnerability url"),
        "modified_date": fields.DateTime(description="vulnerability modified date"),
        "published_date": fields.DateTime(description="vulnerability published date"),
        "body": fields.String(description="vulnerability body in JSON format")
    }
)
errata_package_model = ns.model(
    "ErrataPackageModel",
    {
        "id": fields.String(description="errata id"),
        "type": fields.String(description="errata type"),
        "pkgset_name": fields.String(description="packageset name"),
        "pkgset_date": fields.Date(description="packageset date"),
        "task_id": fields.Integer(description="task id"),
        "task_state": fields.String(description="task state"),
        "task_changed": fields.String(description="task changed date"),
        "subtask_id": fields.Integer(description="subtask id"),
        "pkg_hash": fields.String(description="package hash"),
        "pkg_name": fields.String(description="package name"),
        "pkg_version": fields.String(description="package version"),
        "pkg_release": fields.String(description="package release"),
        "bugs": fields.Nested(
            errata_bug_model,
            description="list of bugs",
            as_list=True,
        ),
        "vulns": fields.Nested(
            errata_vuln_model,
            description="list of vulnerabilities",
            as_list=True
        )
    }
)
errata_packages_model = ns.model(
    "ErrataPackagesModel",
    {
        "pkg_updates": fields.Nested(
            errata_package_model,
            description="list of packages updates",
            as_list=True
        ),
    },
)
errata_branch_model = ns.model(
    "ErrataBranchModel",
    {
        "id": fields.String(description="errata id"),
        "type": fields.String(description="errata type"),
        "pkgset_name": fields.String(description="packageset name"),
        "pkgset_date": fields.DateTime(description="packageset date"),
        "pkg_updates": fields.Nested(
            errata_package_model,
            description="list of packages updates",
            as_list=True
        ),
    },
)
errata_branches_model = ns.model(
    "ErrataBranchesModel",
    {
        "branch_updates": fields.Nested(
            errata_branch_model,
            description="list of branch updates",
            as_list=True
        ),
    },
)
