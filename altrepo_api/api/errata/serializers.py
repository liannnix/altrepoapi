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
        "branches": fields.List(
            fields.String, description="OVAL export available branches"
        ),
    },
)

erratas_ids_json_list_model = ns.model(
    "ErrataJsonPostListModel",
    {"errata_ids": fields.List(fields.String, description="errata ids list")},
)

errata_reference_model = ns.model(
    "ErrataReferenceModel",
    {
        "id": fields.String(description="errata id"),
        "type": fields.String(description="errata type"),
    },
)
erratas_model = ns.model(
    "ErratasModel",
    {
        "erratas": fields.Nested(
            ns.model(
                "ErrataModel",
                {
                    "id": fields.String(description="errata id"),
                    "type": fields.String(description="errata type"),
                    "created": fields.Date(description="errata created date"),
                    "updated": fields.Date(description="errata updated date"),
                    "pkgset_name": fields.String(description="packageset name"),
                    "task_id": fields.Integer(description="task id"),
                    "subtask_id": fields.Integer(description="subtask id"),
                    "task_state": fields.String(description="task state"),
                    "pkg_hash": fields.String(description="package hash"),
                    "pkg_name": fields.String(description="package name"),
                    "pkg_version": fields.String(description="package version"),
                    "pkg_release": fields.String(description="package release"),
                    "references": fields.Nested(
                        errata_reference_model,
                        description="list of references",
                        as_list=True,
                    ),
                },
            ),
            description="list of erratas",
            as_list=True,
        )
    },
)

errata_bug_model = ns.model(
    "ErrataBugModel",
    {
        "id": fields.Integer(description="bug id"),
        "summary": fields.String(description="bug summary"),
        "is_valid": fields.Boolean(description="bug information is valid"),
    },
)
errata_vuln_model = ns.model(
    "ErrataVulnerabilityModel",
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
        "body": fields.String(description="vulnerability body in JSON format"),
        "is_valid": fields.Boolean(description="vulnerability information is valid"),
    },
)
errata_package_update_model = ns.model(
    "ErrataPackageUpdateModel",
    {
        "id": fields.String(description="errata id"),
        "type": fields.String(description="errata type"),
        "created": fields.Date(description="errata created date"),
        "updated": fields.Date(description="errata updated date"),
        "pkgset_name": fields.String(description="packageset name"),
        "task_id": fields.Integer(description="task id"),
        "subtask_id": fields.Integer(description="subtask id"),
        "task_state": fields.String(description="task state"),
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
            as_list=True,
        ),
    },
)
errata_packages_updates_model = ns.model(
    "ErrataPackagesUpdatesModel",
    {
        "packages_updates": fields.Nested(
            errata_package_update_model,
            description="list of packages updates",
            as_list=True,
        ),
    },
)
errata_branch_update_model = ns.model(
    "ErrataBranchUpdateModel",
    {
        "id": fields.String(description="errata id"),
        "type": fields.String(description="errata type"),
        "pkgset_name": fields.String(description="packageset name"),
        "pkgset_date": fields.DateTime(description="packageset date"),
        "packages_updates": fields.Nested(
            errata_package_update_model,
            description="list of packages updates",
            as_list=True,
        ),
    },
)
errata_branches_updates_model = ns.model(
    "ErrataBranchesUpdatesModel",
    {
        "branches_updates": fields.Nested(
            errata_branch_update_model,
            description="list of branch updates",
            as_list=True,
        ),
    },
)


errata_ids_model = ns.model(
    "ErrataIdsListModel",
    {"errata_ids": fields.List(fields.String, description="errata ids list")},
)
