# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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
vuln_reference_model = ns.model(
    "VulnerabilityReferenceModel",
    {
        "name": fields.String(description="refernce name"),
        "url": fields.String(description="refernce link"),
        "tags": fields.List(fields.String, description="reference tags"),
    }
)
vuln_cvss_vector_model = ns.model(
    "VulnerabilityCVSSVectorModel",
    {
        "version": fields.String(description="CVSS vector version"),
        "score": fields.Float(description="CVSS base score"),
        "vector": fields.String(description="CVSS vector"),
    }
)
vulnerability_info_model = ns.model(
    "VulnerabilityInfoModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "vuln_info": fields.Nested(
            vulnerability_model, description="vulnerabilty information"
        ),
        "vuln_references": fields.Nested(
            vuln_reference_model,
            description="Parsed vulnerability references",
            as_list=True,
        ),
        "vuln_cvss_vectors": fields.Nested(
            vuln_cvss_vector_model,
            description="Parsed vulnerability CVSS vectors",
            as_list=True,
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
        "version": fields.String(
            description="package version", attribute="pkg_version"
        ),
        "release": fields.String(
            description="package release", attribute="pkg_release"
        ),
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
        "fixed": fields.Boolean(
            description="is package vulnerability closed by Errata"
        ),
        "cpe_matches": fields.Nested(
            vuln_cpe_match_model,
            description="CPE matches list that package is vulnerable through",
            as_list=True,
        ),
        "fixed_in": fields.Nested(
            vuln_errata_model,
            description="Errata list that closes vulnerability for package",
            as_list=True,
        ),
    },
)
cve_packages_model = ns.model(
    "CveVulnerablePackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "result": fields.List(fields.String, description="Data collection details"),
        "vuln_info": fields.Nested(
            vulnerability_model, description="vulnerabilty information", as_list=True
        ),
        "packages": fields.Nested(
            vulnerable_package_model,
            description="vulnerable packages information",
            as_list=True,
        ),
    },
)


vuln_pkg_last_version_model = ns.model(
    "VulnPackageLastVersionModel",
    {
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "branch": fields.String(description="package set name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
    },
)
vuln_fixes_el_model = ns.model(
    "VulnFixesPackagesElementModel",
    {
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "branch": fields.String(description="package set name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "errata_id": fields.String(description="errata ID"),
        "task_id": fields.Integer(description="task ID"),
        "task_state": fields.String(description="task state"),
        "last_version": fields.Nested(
            vuln_pkg_last_version_model,
            description="last package version and release from repository",
        ),
    },
)
vuln_fixes_model = ns.model(
    "VulnFixesPackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            vuln_fixes_el_model,
            description="vulnerable packages information",
            as_list=True,
        ),
    },
)

vuln_open_el_model = ns.model(
    "VulnOpenPackagesElementModel",
    {
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "branch": fields.String(description="package set name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "last_version": fields.Nested(
            vuln_pkg_last_version_model,
            description="last package version and release from repository",
        ),
    },
)
vuln_open_model = ns.model(
    "VulnOpenPackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            vuln_open_el_model,
            description="vulnerable packages information",
            as_list=True,
        ),
    },
)


cve_task_package_vulns_el_model = ns.model(
    "CveTaskPackageVulnerableElementModel",
    {
        "id": fields.String(description="vulnerability id"),
        "type": fields.String(description="vulnerability type"),
        "link": fields.String(description="vulnerability link"),
    },
)
cve_task_packages_el_model = ns.model(
    "CveTaskPackagesElementModel",
    {
        "subtask": fields.Integer(description="subtasks id"),
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "pkg_name": fields.String(description="source package name"),
        "pkg_version": fields.String(description="package version"),
        "pkg_release": fields.String(description="package release"),
        "branch": fields.String(description="package set name"),
        "errata_id": fields.String(description="errata id"),
        "errata_link": fields.String(description="errata link to errata.altlinux.org"),
        "vulnerabilities": fields.Nested(
            cve_task_package_vulns_el_model,
            description="fixed vulnerabilities list",
            as_list=True,
        ),
    },
)
cve_task_model = ns.model(
    "CveVulnerableTaskModel",
    {
        "packages": fields.Nested(
            cve_task_packages_el_model,
            description="vulnerable packages information",
            as_list=True,
        ),
    },
)

branch_package_vulnerability_model = ns.model(
    "BranchPackageVulnerabilityModel",
    {
        "id": fields.String(description="vulnerability identificator"),
        "cpe_matches": fields.Nested(
            vuln_cpe_match_model,
            description="CPE matches list that package is vulnerable through",
            as_list=True,
        ),
    },
)
branch_vulnerable_package_model = ns.model(
    "BranchVulnerablePackageModel",
    {
        "branch": fields.String(description="packageset name"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "vulneravilities": fields.Nested(
            branch_package_vulnerability_model,
            description="Vulnerability matching info",
            as_list=True,
        ),
        "fixed_in": fields.Nested(
            vuln_errata_model,
            description="Errata list that closes vulnerability for package",
            as_list=True,
        ),
    },
)
branch_cve_packages_model = ns.model(
    "BranchCveVulnerablePackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "result": fields.List(fields.String, description="Data collection details"),
        "vuln_info": fields.Nested(
            vulnerability_model, description="vulnerabilty information", as_list=True
        ),
        "packages": fields.Nested(
            branch_vulnerable_package_model,
            description="vulnerable packages information",
            as_list=True,
        ),
    },
)
