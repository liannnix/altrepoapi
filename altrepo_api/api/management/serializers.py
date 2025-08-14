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
    "ManageVulnerabilityModel",
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
        "type": fields.String(description="errata reference type", required=True),
        "link": fields.String(description="errata reference link", required=True),
    },
)
errata_manage_errata_model = ns.model(
    "ErrataManageErrataModel",
    {
        "is_discarded": fields.Boolean(
            description="is errata discarded", default=False
        ),
        "id": fields.String(description="errata id", required=True),
        "created": fields.DateTime(description="errata created date", required=True),
        "updated": fields.DateTime(description="errata updated date", required=True),
        "type": fields.String(description="errata type", required=True),
        "source": fields.String(description="errata source", required=True),
        "references": fields.Nested(
            errata_manage_reference_el_model,
            description="list of errata references",
            as_list=True,
            required=True,
        ),
        "pkg_hash": fields.String(description="package hash", required=True),
        "pkg_name": fields.String(description="package name", required=True),
        "pkg_version": fields.String(description="package version", required=True),
        "pkg_release": fields.String(description="package release", required=True),
        "pkgset_name": fields.String(description="packageset name", required=True),
        "task_id": fields.Integer(description="task id", required=True),
        "subtask_id": fields.Integer(description="subtask id", required=True),
        "task_state": fields.String(description="task state", required=True),
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
        "user": fields.String(description="errata change originator", required=True),
        "action": fields.String(description="errata manage action", required=True),
        "reason": fields.String(description="errata change reason", required=True),
        "errata": fields.Nested(
            errata_manage_errata_model, description="errata contents", required=True
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

manage_pnc_record_model = ns.model(
    "ManagePncRecordModel",
    {
        "pkg_name": fields.String(description="package name"),
        "pnc_result": fields.String(description="package name comversion"),
        "pnc_type": fields.String(description="package name comversion type"),
        "pnc_state": fields.String(description="package name comversion status"),
        "pnc_source": fields.String(description="package name comversion source"),
    },
)
manage_pnc_change_record_model = ns.model(
    "ManagePncChangeRecordModel",
    {
        "id": fields.String(description="PNC change record identifier"),
        "user": fields.String(description="errata change user"),
        "reason": fields.String(description="errata change reason"),
        "type": fields.String(description="errata change type"),
        "pnc": fields.Nested(
            manage_pnc_record_model,
            description="list of modified PNC records",
        ),
    },
)

cpe_package_el_model = ns.model(
    "CpePackageElementModel",
    {
        "name": fields.String(description="package name"),
        "branch": fields.String(description="package set name"),
    },
)
cpe_records_model = ns.model(
    "CpePackagesModel",
    {
        "cpe": fields.String(description="CPE match string"),
        "state": fields.String(description="CPE match state"),
        "project_name": fields.String(
            attribute="repology_name",
            description="Repology' common project package name",
        ),
        "packages": fields.Nested(
            cpe_package_el_model,
            description="matching packages list",
            as_list=True,
        ),
    },
)

cpe_candidates_response_model = ns.model(
    "CpeCandidatesResponseModel",
    {
        "length": fields.Integer(description="number of CPE matches found"),
        "cpes": fields.Nested(
            cpe_records_model,
            description="list of CPE match candidates",
            as_list=True,
        ),
    },
)
cpe_manage_get_response_model = ns.model(
    "CpeManageGet_responseModel",
    {
        "length": fields.Integer(description="number of CPE matches found"),
        "name": fields.String(description="input package name"),
        "branch": fields.String(description="input package set name"),
        "cpes": fields.Nested(
            cpe_records_model,
            description="list of CPE match candidates",
            as_list=True,
        ),
    },
)

cpe_manage_cpe_model = ns.model(
    "CpeManageCpeModel",
    {
        "cpe": fields.String(description="CPE match string", required=True),
        "project_name": fields.String(
            description="Repology' common project package name", required=True
        ),
        "state": fields.String(description="CPE match state", required=True),
    },
)
cpe_manage_pkg_cve_match_el_model = ns.model(
    "CpeManagePackageCveMatchElementModel",
    {
        "vuln_id": fields.String(description="CVE ID"),
        "cpe": fields.String(description="CVE ID", attribute="pkg_cpe"),
        "is_vulnerable": fields.Boolean(description="package is vulnerable"),
        "pkg_hash": fields.String(description="package hash"),
        "pkg_name": fields.String(description="package name"),
        "pkg_version": fields.String(description="package version"),
        "pkg_release": fields.String(description="package release"),
        "branches": fields.List(
            fields.String(), attribute="branch", description="package in branches"
        ),
    },
)

cpe_manage_model = ns.model(
    "CpeManageModel",
    {
        "user": fields.String(description="CPE change originator", required=True),
        "action": fields.String(description="CPE manage action", required=True),
        "reason": fields.String(description="CPE change reason", required=True),
        "cpe": fields.Nested(
            cpe_manage_cpe_model, description="CPE match record", required=True
        ),
    },
)

cpe_manage_response_model = ns.model(
    "CpeManageResponseModel",
    {
        "user": fields.String(description="CPE change originator"),
        "action": fields.String(description="CPE manage action"),
        "reason": fields.String(description="CPE change reason"),
        "message": fields.String(description="API response message"),
        "cpe": fields.Nested(
            cpe_manage_cpe_model,
            description="list of CPE match records",
        ),
        "package_name": fields.String(
            description="exact package name to restrict results on"
        ),
        "related_packages": fields.List(
            fields.String,
            description="packages names are related to modified CPE records",
        ),
        "related_cve_ids": fields.List(
            fields.String,
            description="CVE IDs are related to modified CPE records",
        ),
        "cpe_records": fields.Nested(
            manage_pnc_record_model,
            description="list of modified CPE match records",
            as_list=True,
        ),
        "cpe_change_records": fields.Nested(
            manage_pnc_change_record_model,
            description="list of CPE match change records",
            as_list=True,
        ),
        "errata_records": fields.Nested(
            errata_manage_errata_model,
            description="modified Errata records contents",
            as_list=True,
        ),
        "errata_change_records": fields.Nested(
            errata_manage_errata_change_model,
            description="Errata change records contents",
            as_list=True,
        ),
        "packages_cve_matches": fields.Nested(
            cpe_manage_pkg_cve_match_el_model,
            description="list of updated packages' CVE match records",
            as_list=True,
        ),
    },
)

pkg_open_vuln_info_el_model = ns.model(
    "PackageOpenVulnInfoElementModel",
    {
        "id": fields.String(description="vulnerability ID"),
        "type": fields.String(description="vulnerability type"),
        "severity": fields.String(description="vulnerability severity"),
    },
)
pkg_imgs_el_model = ns.model(
    "PackageImagesElementModel",
    {
        "tag": fields.String(description="Image package set tag"),
        "file": fields.String(description="Image file name"),
        "show": fields.String(description="hide - hide image, show - show image"),
    },
)
pkg_open_vulns_el_vulns = ns.model(
    "PackageOpenVulnsElementModel",
    {
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "pkg_name": fields.String(description="package name"),
        "pkg_version": fields.String(description="package version"),
        "pkg_release": fields.String(description="package release"),
        "branch": fields.String(description="package set name"),
        "vulns": fields.Nested(
            pkg_open_vuln_info_el_model,
            description="list of open package vulnerabilities",
            as_list=True,
        ),
        "images": fields.Nested(
            pkg_imgs_el_model,
            description="images of what the package includes",
            as_list=True,
        ),
    },
)
pkg_open_vulns = ns.model(
    "PackageOpenVulnsModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            pkg_open_vulns_el_vulns,
            description="list of packages with open vulnerabilities",
            as_list=True,
        ),
        "images": fields.Nested(
            pkg_imgs_el_model,
            description="all images",
            as_list=True,
        ),
    },
)

pkgs_unmapped_model = ns.model(
    "PackagesUnmappedModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.List(
            fields.String,
            description="list of packages that not mapped to any project",
            as_list=True,
        ),
    },
)

supported_branches_model = ns.model(
    "SupportedBranchesModel",
    {
        "length": fields.Integer(description="number of supported branches found"),
        "branches": fields.List(fields.String, description="supported branches list"),
    },
)

maintainer_list_el_model = ns.model(
    "MaintainerListElementModel",
    {
        "name": fields.String(description="maintainer name"),
        "nickname": fields.String(description="maintainer nickname"),
    },
)
maintainer_list_model = ns.model(
    "MaintainerListModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of maintainers found"),
        "maintainers": fields.Nested(
            maintainer_list_el_model,
            description="maintainers list",
            as_list=True,
        ),
    },
)

pnc_manage_pnc_model = ns.model(
    "PncManagePncModel",
    {
        "package_name": fields.String(
            description="PNC source package name", required=True
        ),
        "project_name": fields.String(
            description="PNC common project name", required=True
        ),
        "state": fields.String(description="PNC record state", required=True),
        "source": fields.String(description="PNC record source", required=True),
    },
)
pnc_manage_model = ns.model(
    "PncManageModel",
    {
        "user": fields.String(description="PNC change originator", required=True),
        "action": fields.String(description="PNC manage action", required=True),
        "reason": fields.String(description="PNC change reason", required=True),
        "pnc": fields.Nested(
            pnc_manage_pnc_model, description="PNC record", as_list=False, required=True
        ),
    },
)

pnc_manage_get_model = ns.model(
    "PncManageGetModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "pncs": fields.Nested(
            manage_pnc_record_model, description="list of PNC records", as_list=True
        ),
    },
)

pnc_manage_response_model = ns.model(
    "PncManageResponseModel",
    {
        "user": fields.String(description="PNC change originator"),
        "action": fields.String(description="PNC manage action"),
        "reason": fields.String(description="PNC change reason"),
        "message": fields.String(description="API response message"),
        "pnc_records": fields.Nested(
            manage_pnc_record_model,
            description="list of modified PNC records",
            as_list=True,
        ),
        "pnc_change_records": fields.Nested(
            manage_pnc_change_record_model,
            description="list of PNC change records",
            as_list=True,
        ),
        "errata_records": fields.Nested(
            errata_manage_errata_model,
            description="modified Errata records contents",
            as_list=True,
        ),
        "errata_change_records": fields.Nested(
            errata_manage_errata_change_model,
            description="Errata change records contents",
            as_list=True,
        ),
        "related_cve_ids": fields.List(
            fields.String,
            description="CVE IDs are related to modified PNC records",
        ),
    },
)

pnc_packages_el_model = ns.model(
    "PncPackagesElementModel",
    {
        "pkg_name": fields.String(description="package name"),
        "pnc_type": fields.String(description="package name conversion type"),
        "pnc_source": fields.String(description="package name conversion source"),
    },
)
pnc_list_el_model = ns.model(
    "PncListElementModel",
    {
        "pnc_result": fields.String(description="package name conversion"),
        "pnc_state": fields.String(description="package name conversion status"),
        "packages": fields.Nested(
            pnc_packages_el_model,
            description="list of packages for PNC record",
            as_list=True,
        ),
        "cpes": fields.Nested(
            manage_pnc_record_model,
            description="list of cpes for PNC record",
            as_list=True,
        ),
    },
)
pnc_list_model = ns.model(
    "PncListModal",
    {
        "request_args": fields.Raw(description="request arguments"),
        "pncs": fields.Nested(
            pnc_list_el_model, description="list of PNC records", as_list=True
        ),
    },
)

vuln_errata_el_model = ns.model(
    "VulnerabilityErrataElementModel",
    {
        "id": fields.String(description="errata id"),
        "task_state": fields.String(description="task state"),
    },
)
vuln_list_el_model = ns.model(
    "VulnerabilityListElementModel",
    {
        "id": fields.String(description="vulnerability id"),
        "severity": fields.String(description="vulnerability severity"),
        "summary": fields.String(description="vulnerability summary"),
        "modified": fields.DateTime(description="vulnerability modified date"),
        "published": fields.DateTime(description="vulnerability published date"),
        "erratas": fields.Nested(
            vuln_errata_el_model,
            description="list of errata IDs in which the vulnerability was fixed",
            as_list=True,
        ),
        "cpes": fields.List(
            fields.String,
            description="list of CPE records for this vulnerability",
        ),
        "our": fields.Boolean(description="Our"),
    },
)
vuln_list_model = ns.model(
    "VulnerabilityListModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(
            description="number of vulnerabilities found on the page"
        ),
        "vulns": fields.Nested(
            vuln_list_el_model, description="list of vulnerability", as_list=True
        ),
    },
)

sa_manage_pcm_el_model = ns.model(
    "SamanageAffectedPcmElementModel",
    {
        "package": fields.String(description="package name"),
        "cve": fields.String(description="CVE id"),
    },
)
sa_manage_pkg_version_el_model = ns.model(
    "SaManagePackageVersionRangeModel",
    {
        "begin": fields.String(description="version range begin"),
        "begin_exclude": fields.Boolean(description="is version range begin excluded"),
        "end": fields.String(description="version range end"),
        "end_exclude": fields.Boolean(description="is version range end excluded"),
    },
)
sa_manage_errata_json_model = ns.model(
    "SaManageErrataJsonModel",
    {
        "type": fields.String(description="SA errata type", required=True),
        "action": fields.String(description="SA errata type", required=True),
        "is_public": fields.Boolean(description="is SA errata public", required=True),
        "reason": fields.String(description=" SA errata reason", required=True),
        "description": fields.String(
            description=" SA errata description", required=True
        ),
        "vuln_id": fields.String(description="vulnerability identifier", required=True),
        "vuln_cpe": fields.String(
            description="CPE string", required=False, default=None
        ),
        "branches": fields.List(
            fields.String,
            description="list of branches",
            # XXX: make it optional here due to unused on server for a now
            required=False,
            default=list(),
        ),
        "pkg_name": fields.String(
            description="package name", required=False, default=""
        ),
        "pkg_evr": fields.String(
            description="package EVR string", required=False, default=""
        ),
        "pkg_versions": fields.Nested(
            sa_manage_pkg_version_el_model,
            description="list of package version ranges",
            as_list=True,
            # XXX: make it optional here due to unused on server for a now
            required=False,
            default=list(),
        ),
        "references": fields.Nested(
            errata_manage_reference_el_model,
            description="list of references",
            as_list=True,
            required=False,
            default=list(),
        ),
        "extra": fields.Raw(
            description="SA errata extra details mapping", required=False, default=None
        ),
    },
)
sa_manage_errata_model = ns.clone(
    "SaManageErrataModel",
    errata_manage_errata_model,
    {
        "json": fields.Nested(
            sa_manage_errata_json_model,
            description="errata SA JSON contents",
            as_list=False,
        )
    },
)
sa_manage_list_model = ns.model(
    "SaManageListResponseModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of SA errata records found in DB"),
        "errata": fields.Nested(
            sa_manage_errata_model,
            description="errata contents",
            as_list=True,
        ),
    },
)
sa_manage_create_model = ns.model(
    "SaManageCreatePayloadModel",
    {
        "errata_json": fields.Nested(
            sa_manage_errata_json_model,
            description="new SA errata JSON contents",
            required=True,
        )
    },
)
sa_manage_discard_model = ns.clone(
    "SaManageDiscardPayloadModel",
    sa_manage_create_model,
    {
        "reason": fields.String(
            description="SA errata discard reason",
            required=True,
        )
    },
)
sa_manage_update_model = ns.clone(
    "SaManageUpdatePayloadModel",
    sa_manage_create_model,
    {
        "reason": fields.String(
            description="SA errata update reason",
            required=True,
        ),
        "prev_errata_json": fields.Nested(
            sa_manage_errata_json_model,
            description="previous SA Errata JSON state contents",
            required=True,
        ),
    },
)
sa_manage_response_model = ns.model(
    "SaManageResponseModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "result": fields.String(description="Errata Server operation result"),
        "errata": fields.Nested(
            sa_manage_errata_model,
            description="errata records",
            as_list=True,
        ),
        "errata_change": fields.Nested(
            errata_manage_errata_change_model,
            description="errata change records",
            as_list=True,
        ),
        "affected_pcm": fields.Nested(
            sa_manage_pcm_el_model,
            description="affected package to CVE matches",
            as_list=True,
        ),
    },
)

change_history_cpe_info_model = ns.model(
    "ChangeHistoryCpeInfoModel",
    {
        "cpe": fields.String(description="CPE identifier", required=True),
        "state": fields.String(
            description="current state of the CPE (active/inactive)",
            enum=["active", "inactive"],
            required=True,
        ),
        "project_name": fields.String(description="associated project name"),
    },
)
change_history_pnc_info_model = ns.model(
    "ChangeHistoryPncInfoModel",
    {
        "state": fields.String(
            description="Package name conversion state (active/inactive)",
            enum=["active", "inactive"],
            required=True,
        ),
        "package": fields.String(description="Package name"),
        "project_name": fields.String(
            description="Project name associated with the package"
        ),
    },
)
change_history_detail_model = ns.model(
    "ChangeHistoryDetailModel",
    {
        "cpe": fields.Nested(
            change_history_cpe_info_model,
            allow_null=True,
            description="CPE-related information",
        ),
        "pnc": fields.Nested(
            change_history_pnc_info_model,
            allow_null=True,
            description="PNC-related information",
        ),
        "name": fields.String(description="package name"),
        "hash": fields.String(description="package unique hash identifier"),
        "task_id": fields.String(description="task number"),
        "version": fields.String(description="package version"),
        "branch": fields.String(description="package set name"),
        "subtask_id": fields.String(description="subtask number"),
        "release": fields.String(description="package release"),
        "task_state": fields.String(description="current task state"),
    },
)
change_history_el_model = ns.model(
    "ChangeHistoryElementModel",
    {
        "change_type": fields.String(
            required=True,
            enum=["create", "update", "discard"],
            description="type of change operation",
        ),
        "module": fields.String(
            required=True, enum=["errata", "pnc"], description="affected system module"
        ),
        "errata_id": fields.String(description="errata identifier"),
        "message": fields.String(description="change description"),
        "package_name": fields.String(description="package name (for PNC changes)"),
        "result": fields.String(
            description="operation result status (for PNC changes)"
        ),
        "details": fields.Nested(
            change_history_detail_model,
            required=True,
            description="detailed change information",
        ),
    },
)
change_history_model = ns.model(
    "ChangeHistoryModel",
    {
        "transaction_id": fields.String(required=True, description="transaction ID"),
        "event_date": fields.DateTime(
            required=True, description="timestamp of the change event"
        ),
        "author": fields.String(
            required=True, description="user who initiated the change"
        ),
        "changes": fields.Nested(
            change_history_el_model,
            description="a detailed list of the history of changes in transaction",
            as_list=True,
            required=True,
        ),
    },
)
change_history_response_model = ns.model(
    "ChangeHistoryResponseModel",
    {
        "request_args": fields.Raw(required=True, description="request arguments"),
        "length": fields.Integer(
            required=True, description="number of changes history found"
        ),
        "change_history": fields.Nested(
            change_history_model,
            description="list of history of transactions changes",
            as_list=True,
            required=True,
        ),
    },
)
