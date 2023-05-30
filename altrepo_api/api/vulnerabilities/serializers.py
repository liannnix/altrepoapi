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

vulnerability_model = ns.model(
    "VulnerabilityModel",
    {
        "id": fields.String(description="vulnerability id"),
        "summary": fields.String(description="description summary"),
        "url": fields.String(description="origin URL"),
        "severity": fields.String(description="severity level"),
        "score": fields.Float(description="severity score"),
        "published": fields.DateTime(description="published date"),
        "modified": fields.DateTime(description="modified date"),
        "refs": fields.List(fields.String, description="vulnerability references"),
        "json": fields.Raw(description="vulnerability original JSON"),
    },
)
vulnerability_info_model = ns.model(
    "VulnerabilityInfoModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "vuln_info": fields.Nested(
            vulnerability_model, description="vulnerabilty information"
        ),
    },
)

vuln_cpe_match_version_model = ns.model(
    "VulnerabilityCpeMatchVersionModel",
    {
        "version_start": fields.String(description="CPE match start version"),
        "version_end": fields.String(description="CPE match end version"),
        "version_start_excluded": fields.Boolean(
            description="is CPE match start version excluded"
        ),
        "version_end_excluded": fields.Boolean(
            description="is CPE match end version excluded"
        ),
    },
)
vuln_cpe_match_model = ns.model(
    "VulnerabilityCpeMatchModel",
    {
        "cpe": fields.String(description="CPE string"),
        "versions": fields.Nested(
            vuln_cpe_match_version_model, description="CPE match versions range"
        ),
    },
)
vuln_errata_model = ns.model(
    "VulnerabilityErrataModel",
    {
        "id": fields.String(description="Errata ID"),
        "branch": fields.String(description="packageset name"),
        "task_id": fields.Integer(description="task ID"),
        "subtask_id": fields.Integer(description="subtask ID"),
        "task_state": fields.String(description="task state"),
        "hash": fields.String(description="package hash", attribute="pkg_hash"),
        "name": fields.String(description="package name", attribute="pkg_name"),
        "version": fields.String(description="package version", attribute="pkg_version"),
        "release": fields.String(description="package release", attribute="pkg_release"),
        "vulns": fields.List(
            fields.String,
            description="Errata closed vulnerabilities list",
        ),
    },
)
vulnerable_package_model = ns.model(
    "VulnerablePackageModel",
    {
        "branch": fields.String(description="packageset name"),
        "hash": fields.String(description="package hash"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "vuln_id": fields.String(description="vulnerability id"),
        "vulnerable": fields.Boolean(description="is package vulnerable"),
        "fixed": fields.Boolean(description="is package vulnerability closed by Errata"),
        "cpe_matches": fields.Nested(
            vuln_cpe_match_model,
            description="CPE matches list that package is vulnerable through",
        ),
        "fixed_in": fields.Nested(
            vuln_errata_model,
            description="Errata list that closes vulnerability for package",
        ),
    },
)
cve_packages_model = ns.model(
    "CveVulnerablePackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "vuln_info": fields.Nested(
            vulnerability_model, description="vulnerabilty information"
        ),
        "packages": fields.Nested(
            vulnerable_package_model, description="vulnerable packages information"
        ),
    },
)
