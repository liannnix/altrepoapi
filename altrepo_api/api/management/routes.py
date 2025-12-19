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

from flask import g
from flask_restx import Resource

from altrepo_api.settings import namespace as settings
from altrepo_api.utils import get_logger, url_logging
from altrepo_api.api.auth.decorators import token_required
from altrepo_api.api.base import (
    GET_RESPONSES_400_404,
    GET_RESPONSES_404,
    POST_RESPONSES_400_404_409,
    run_worker,
)
from altrepo_api.api.metadata import with_metadata
from altrepo_api.api.errata.endpoints.branch import BranchesUpdates, ErrataBranches
from altrepo_api.api.errata.endpoints.package import PackagesUpdates
from altrepo_api.api.errata.endpoints.search import FindErratas
from altrepo_api.api.errata.parsers import find_erratas_args
from altrepo_api.api.errata.serializers import (
    errata_branch_update_model as _errata_branch_update_model,
    errata_branches_model,
    errata_branches_updates_model as _errata_branches_updates_model,
    errata_bug_model as _errata_bug_model,
    errata_last_changed_el_model as _errata_last_changed_el_model,
    errata_last_changed_model as _errata_last_changed_model,
    errata_package_update_model as _errata_package_update_model,
    errata_packages_updates_model as _errata_packages_updates_model,
    errata_vuln_model as _errata_vuln_model,
    erratas_ids_json_list_model,
    pkgs_el_model as _pkgs_el_model,
    vulns_el_model as _vulns_el_model,
)
from altrepo_api.api.task_progress.endpoints.packageset import AllTasksBraches
from altrepo_api.api.task_progress.serializers import all_tasks_branches_model
from altrepo_api.api.vulnerabilities.endpoints.excluded import VulnExcluded
from altrepo_api.api.vulnerabilities.endpoints.fixes import VulnFixes
from altrepo_api.api.vulnerabilities.endpoints.packages import PackagesByOpenVuln
from altrepo_api.api.vulnerabilities.endpoints.vuln import VulnInfo
from altrepo_api.api.vulnerabilities.parsers import (
    bdu_info_args,
    cve_info_args,
    ghsa_info_args,
    vuln_info_args,
)
from altrepo_api.api.vulnerabilities.serializers import (
    vuln_fixes_el_model as _vuln_fixes_el_model,
    vuln_fixes_model as _vuln_fixes_model,
    vuln_open_el_model as _vuln_open_el_model,
    vuln_open_model as _vuln_open_model,
    vuln_pkg_last_version_model as _vuln_pkg_last_version_model,
    vulnerability_model as _vulnerability_model,
    vuln_cvss_vector_element_model as _vuln_cvss_vector_element_model,
    vuln_configuration_element_model as _vuln_configuration_element_model,
    vuln_reference_element_model as _vuln_reference_element_model,
    vuln_parsed_model as _vuln_parsed_model,
    vulnerability_info_model as _vulnerability_info_model,
)

from .endpoints.change_history import ChangeHistory, ErrataChangeHistory
from .endpoints.cpe import CPECandidates, CPEList, ManageCpe
from .endpoints.comment_list import CommentsList
from .endpoints.comments import Comments
from .endpoints.default_reasons import DefaultReasons
from .endpoints.default_reasons_list import DefaultReasonsList
from .endpoints.errata import ManageErrata
from .endpoints.errata_user import (
    ErrataUserInfo,
    ErrataUserTag,
    ErrataUserLastActivities,
    ErrataUserAliases,
    ErrataUserSubscriptions,
    ErrataEntitySubscriptions,
)
from .endpoints.errata_user_tracking import ErrataUserTracking
from .endpoints.packages_open_vulns import (
    PackagesImageList,
    PackagesMaintainerList,
    PackagesOpenVulns,
    PackagesSupportedBranches,
)
from .endpoints.packages_unmapped import PackagesUnmapped
from .endpoints.pnc import ManagePnc, PncList
from .endpoints.sa import ListSa, ManageSa
from .endpoints.task_info import TaskInfo
from .endpoints.task_list import TaskList
from .endpoints.vuln_list import VulnList
from .endpoints.vulns_info import VulnsInfo
from .endpoints.vuln_status import VulnStatus
from .endpoints.vuln_status_list import VulnStatusList
from .endpoints.vuln_status_history import VulnStatusHistory
from .endpoints.vuln_status_select_next import VulnStatusSelectNext
from .namespace import get_namespace
from .parsers import (
    change_history_args,
    comments_list_args,
    cpe_candidates_args,
    cpe_list_args,
    cpe_manage_args,
    cpe_manage_get_args,
    errata_manage_args,
    errata_manage_get_args,
    maintainer_list_args,
    pkgs_open_vulns_args,
    pkgs_unmapped_args,
    pnc_list_args,
    pnc_manage_args,
    pnc_manage_get_args,
    sa_list_args,
    sa_manage_args,
    task_list_args,
    vuln_list_args,
    default_reasons_list_args,
    vuln_status_list_args,
    vuln_status_history_args,
    vuln_status_manage_args,
    vuln_status_select_next_args,
    errata_user_tag_args,
    errata_user_info_args,
    errata_user_last_activities_args,
    errata_user_aliases_get_args,
    errata_user_aliases_post_args,
    errata_user_subscriptions_args,
    errata_user_tracking_args,
    errata_entity_subscriptions_args,
    image_list_args,
)
from .serializers import (
    change_history_response_model,
    comment_manage_create_model,
    comment_list_model,
    comment_manage_response_model,
    comment_manage_discard_model,
    comment_manage_update_model,
    cpe_candidates_response_model,
    cpe_manage_get_response_model,
    cpe_manage_model,
    cpe_manage_response_model,
    errata_change_history_model,
    errata_manage_get_response_model,
    errata_manage_model,
    errata_manage_response_model,
    maintainer_list_model,
    pkg_open_vulns,
    pkgs_unmapped_model,
    pnc_list_model,
    pnc_manage_get_model,
    pnc_manage_model,
    pnc_manage_response_model,
    sa_manage_create_model,
    sa_manage_discard_model,
    sa_manage_list_model,
    sa_manage_response_model,
    sa_manage_update_model,
    supported_branches_model,
    task_info_model,
    task_list_model,
    vuln_ids_json_list_model,
    vuln_ids_json_post_list_model,
    vuln_list_model,
    default_reasons_list_model,
    default_reasons_manage_model,
    default_reason_response_model,
    vuln_status_manage_create_model,
    vuln_status_list_response_model,
    vuln_status_response_model,
    vuln_status_history_model,
    vuln_status_select_next_model,
    errata_user_info_model,
    errata_user_tag_model,
    errata_user_last_activities_model,
    errata_user_aliases_model,
    errata_user_subscriptions_request_model,
    errata_user_subscription_model,
    errata_user_subscriptions_model,
    errata_user_tracking_model,
    image_list_model,
)

ns = get_namespace()

logger = get_logger(__name__)

# register imported models
errata_last_changed_model = ns.clone(
    "ErrataLastChangedModel", _errata_last_changed_model
)
errata_last_changed_el_model = ns.clone(
    "ErrataLastChangedElementModel", _errata_last_changed_el_model
)
pkgs_el_model = ns.clone("PackagesElementModel", _pkgs_el_model)
vulns_el_model = ns.clone("VulnerabilitiesElementModel", _vulns_el_model)

errata_packages_updates_model = ns.clone(
    "ErrataPackagesUpdatesModel", _errata_packages_updates_model
)
errata_package_update_model = ns.clone(
    "ErrataPackageUpdateModel", _errata_package_update_model
)
errata_bug_model = ns.clone("ErrataBugModel", _errata_bug_model)
errata_vuln_model = ns.clone("ErrataVulnerabilityModel", _errata_vuln_model)

errata_branches_updates_model = ns.clone(
    "ErrataBranchesUpdatesModel", _errata_branches_updates_model
)
errata_branch_update_model = ns.clone(
    "ErrataBranchUpdateModel", _errata_branch_update_model
)

vuln_open_model = ns.clone("VulnOpenPackagesModel", _vuln_open_model)
vuln_open_el_model = ns.clone("VulnOpenPackagesElementModel", _vuln_open_el_model)
vuln_pkg_last_version_model = ns.clone(
    "VulnPackageLastVersionModel", _vuln_pkg_last_version_model
)
vuln_fixes_model = ns.clone("VulnFixesPackagesModel", _vuln_fixes_model)
vuln_fixes_el_model = ns.clone("VulnFixesPackagesElementModel", _vuln_fixes_el_model)
vuln_pkg_last_version_model = ns.clone(
    "VulnPackageLastVersionModel", _vuln_pkg_last_version_model
)
vulnerability_model = ns.clone("VulnerabilityModel", _vulnerability_model)
vuln_cvss_vector_element_model = ns.clone(
    "VulnerabilityCVSSVectorElelementModel", _vuln_cvss_vector_element_model
)
vuln_reference_element_model = ns.clone(
    "VulnerabilityReferenceElementModel", _vuln_reference_element_model
)
vuln_configuration_element_model = ns.clone(
    "VulnerabilityConfigurationElementModel", _vuln_configuration_element_model
)
vulnerability_parsed_model = ns.clone(
    "VulnerabilityParsedDetailsModel", _vuln_parsed_model
)
vulnerability_info_model = ns.clone("VulnerabilityInfoModel", _vulnerability_info_model)


@with_metadata(TaskList, ns, logger, require_auth=True)
@ns.route(
    "/task/list",
    doc={
        "description": "Get a list of tasks in DONE status."
        "You can also search for issues by ID, task owner, "
        "component or Vulnerability.",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeTaskList(Resource):
    @ns.expect(task_list_args)
    @ns.marshal_with(task_list_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = task_list_args.parse_args(strict=True)
        w = TaskList(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/task/info/<int:id>",
    doc={
        "description": "Get information about the task in the state "
        "'DONE' and a list of vulnerabilities for subtasks "
        "based on task ID.",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeTaskInfo(Resource):
    # @ns.expect()
    @ns.marshal_with(task_info_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self, id):
        url_logging(logger, g.url)
        args = {}
        w = TaskInfo(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)


@ns.route("/task/all_tasks_branches")
@ns.doc(
    description="Get branches list for last tasks",
    responses=GET_RESPONSES_404,
    security="Bearer",
)
class routeAllTasksBranches(Resource):
    # @ns.expect()
    @ns.marshal_with(ns.clone("AllTasksBranchesModel", all_tasks_branches_model))
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = AllTasksBraches(g.connection, **args)
        return run_worker(worker=w, args=args)


@with_metadata(VulnList, ns, logger, require_auth=True)
@ns.route(
    "/vuln/list",
    doc={
        "description": "Get vulnerability list",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeVulnList(Resource):
    @ns.expect(vuln_list_args)
    @ns.marshal_with(vuln_list_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = vuln_list_args.parse_args(strict=True)
        w = VulnList(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/vuln/info",
    doc={
        "description": "Find vulnerability information.",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeVulnsInfo(Resource):
    @ns.expect(vuln_ids_json_post_list_model)
    @ns.marshal_with(vuln_ids_json_list_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def post(self):
        url_logging(logger, g.url)
        w = VulnsInfo(g.connection, json_data=ns.payload)
        return run_worker(
            worker=w, run_method=w.post, check_method=w.check_params_post, ok_code=200
        )


@ns.route(
    "/vuln/cve",
    doc={
        "description": "Get CVE information",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeCveInfo(Resource):
    @ns.expect(cve_info_args)
    @ns.marshal_with(vulnerability_info_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = cve_info_args.parse_args(strict=True)
        w = VulnInfo(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/vuln/cve/fixes",
    doc={
        "description": (
            "Get a list of packages in which the specified CVE vulnerability is closed."
        ),
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeVulnerableCveFixes(Resource):
    @ns.expect(cve_info_args)
    @ns.marshal_with(vuln_fixes_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = cve_info_args.parse_args(strict=True)
        w = VulnFixes(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/vuln/cve/excluded",
    doc={
        "description": (
            "Get a list of packages where the specified CVE vulnerability is excluded."
        ),
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeVulnerableCveExcluded(Resource):
    @ns.expect(cve_info_args)
    @ns.marshal_with(vuln_fixes_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = cve_info_args.parse_args(strict=True)
        w = VulnExcluded(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/vuln/bdu",
    doc={
        "description": "Get BDU information",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeBduInfo(Resource):
    @ns.expect(bdu_info_args)
    @ns.marshal_with(vulnerability_info_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = bdu_info_args.parse_args(strict=True)
        w = VulnInfo(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/vuln/bdu/fixes",
    doc={
        "description": (
            "Get a list of packages in which the specified BDU vulnerability is closed."
        ),
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeVulnerableBduFixes(Resource):
    @ns.expect(bdu_info_args)
    @ns.marshal_with(vuln_fixes_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = bdu_info_args.parse_args(strict=True)
        w = VulnFixes(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/vuln/ghsa",
    doc={
        "description": "Get GHSA information",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeGHSAInfo(Resource):
    @ns.expect(ghsa_info_args)
    @ns.marshal_with(vulnerability_info_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = ghsa_info_args.parse_args(strict=True)
        w = VulnInfo(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/vuln/ghsa/fixes",
    doc={
        "description": (
            "Get a list of packages in which "
            "the specified GHSA vulnerability is closed."
        ),
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeVulnerableGHSAFixes(Resource):
    @ns.expect(ghsa_info_args)
    @ns.marshal_with(vuln_fixes_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = ghsa_info_args.parse_args(strict=True)
        w = VulnFixes(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/vuln/open/packages",
    doc={
        "description": (
            "Get a list of packages in which the specified vulnerability is open."
        ),
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routePackagesByOpenVuln(Resource):
    @ns.expect(vuln_info_args)
    @ns.marshal_with(vuln_open_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = vuln_info_args.parse_args(strict=True)
        w = PackagesByOpenVuln(g.connection, **args)
        return run_worker(worker=w, args=args)


RESPONSES_400_404 = {
    200: "Data loaded",
    400: "Request payload validation error",
    404: "Requested data not found in database",
}
RESPONSES_400_409 = {
    200: "Data loaded",
    400: "Request payload validation error",
    409: "Requests payload inconsistent with DB contents",
}
RESPONSES_400_404_409 = {
    200: "Data loaded",
    400: "Request payload validation error",
    404: "Requested data not found in database",
    409: "Requests payload inconsistent with DB contents",
}
GET_RESPONSES_400_404_409 = {
    200: "OK",
    400: "Request arguments validation error",
    404: "Requested data not found in database",
    409: "Request arguments is inconsistent with DB contents",
}


@ns.route("/errata/manage")
class routeManageErrata(Resource):
    @ns.doc(
        description="Get errata info.",
        responses=GET_RESPONSES_400_404_409,
        security="Bearer",
    )
    @ns.expect(errata_manage_get_args)
    @ns.marshal_with(errata_manage_get_response_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = errata_manage_get_args.parse_args(strict=True)
        w = ManageErrata(g.connection, payload={}, **args)
        return run_worker(worker=w, args=args)

    @ns.doc(
        description="Update errata version with new contents.",
        responses=RESPONSES_400_404_409,
        security="Bearer",
    )
    @ns.expect(errata_manage_model, errata_manage_args)
    @ns.marshal_with(errata_manage_response_model)
    @token_required("errata_manage_update")
    def put(self):
        url_logging(logger, g.url)
        args = errata_manage_args.parse_args(strict=False)
        w = ManageErrata(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w, run_method=w.put, check_method=w.check_params_put, ok_code=200
        )

    @ns.doc(
        description="Register new errata record.",
        responses=RESPONSES_400_409,
        security="Bearer",
    )
    @ns.expect(errata_manage_model, errata_manage_args)
    @ns.marshal_with(errata_manage_response_model)
    @token_required("errata_manage_create")
    def post(self):
        url_logging(logger, g.url)
        args = errata_manage_args.parse_args(strict=False)
        w = ManageErrata(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w, run_method=w.post, check_method=w.check_params_post, ok_code=200
        )

    @ns.doc(
        description="Discard errata record.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(errata_manage_model, errata_manage_args)
    @ns.marshal_with(errata_manage_response_model)
    @token_required("errata_manage_discard")
    def delete(self):
        url_logging(logger, g.url)
        args = errata_manage_args.parse_args(strict=False)
        w = ManageErrata(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w,
            run_method=w.delete,
            check_method=w.check_params_delete,
            ok_code=200,
        )


@ns.route(
    "/errata/change_history",
    doc={
        "description": "Get errata change history.",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeErrataChangeHistory(Resource):
    @ns.expect(errata_manage_get_args)
    @ns.marshal_with(errata_change_history_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = errata_manage_get_args.parse_args(strict=True)
        w = ErrataChangeHistory(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/errata/errata_branches",
    doc={
        "description": "Get list of branches form errata history.",
        "responses": GET_RESPONSES_404,
        "security": "Bearer",
    },
)
class routeErrataBranches(Resource):
    @ns.marshal_with(ns.clone("ErrataBranchesModel", errata_branches_model))
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = ErrataBranches(g.connection, **args)
        return run_worker(worker=w, args=args)


@with_metadata(FindErratas, ns, logger, require_auth=True)
@ns.route(
    "/errata/find_erratas",
    doc={
        "description": "Find errata by ID, vulnerability ID or package name.",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeFindErratas(Resource):
    @ns.expect(find_erratas_args)
    @ns.marshal_with(errata_last_changed_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = find_erratas_args.parse_args(strict=True)
        w = FindErratas(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/errata/packages_updates",
    doc={
        "description": "Get information about package update erratas",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routePackagesUpdates(Resource):
    @ns.expect(ns.clone("ErrataJsonPostListModel", erratas_ids_json_list_model))
    @ns.marshal_with(errata_packages_updates_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = PackagesUpdates(g.connection, json_data=ns.payload)
        return run_worker(worker=w, args=args, run_method=w.post, ok_code=200)


@ns.route(
    "/errata/branches_updates",
    doc={
        "description": "Get information about branch update erratas",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeBranchesUpdates(Resource):
    @ns.expect(ns.clone("ErrataJsonPostListModel", erratas_ids_json_list_model))
    @ns.marshal_with(errata_branches_updates_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = BranchesUpdates(g.connection, json_data=ns.payload)
        return run_worker(worker=w, args=args, run_method=w.post, ok_code=200)


@ns.route(
    "/cpe/candidates",
    doc={
        "description": "Get CPE candidates",
        "responses": GET_RESPONSES_404,
        "security": "Bearer",
    },
)
class routeCpeCandidates(Resource):
    @ns.expect(cpe_candidates_args)
    @ns.marshal_with(cpe_candidates_response_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = cpe_candidates_args.parse_args(strict=True)
        w = CPECandidates(g.connection, **args)
        return run_worker(worker=w, args=args)


@with_metadata(CPEList, ns, logger, require_auth=True)
@ns.route(
    "/cpe/list",
    doc={
        "description": "Get CPE list",
        "responses": GET_RESPONSES_404,
        "security": "Bearer",
    },
)
class routeCpeList(Resource):
    @ns.expect(cpe_list_args)
    @ns.marshal_with(cpe_candidates_response_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = cpe_list_args.parse_args(strict=True)
        w = CPEList(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route("/cpe/manage")
class routeManageCpe(Resource):
    @ns.doc(
        description="Get CPE records info.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(cpe_manage_get_args)
    @ns.marshal_with(cpe_manage_get_response_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = cpe_manage_get_args.parse_args(strict=True)
        w = ManageCpe(g.connection, payload={}, **args)
        return run_worker(worker=w, args=args)

    @ns.doc(
        description="Update CPE records.",
        responses=RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(cpe_manage_model, cpe_manage_args)
    @ns.marshal_with(cpe_manage_response_model)
    @token_required("cpe_manage_update")
    def put(self):
        url_logging(logger, g.url)
        args = cpe_manage_args.parse_args(strict=False)
        w = ManageCpe(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w, run_method=w.put, check_method=w.check_params_put, ok_code=200
        )

    @ns.doc(
        description="Register new CPE records.",
        responses=RESPONSES_400_409,
        security="Bearer",
    )
    @ns.expect(cpe_manage_model, cpe_manage_args)
    @ns.marshal_with(cpe_manage_response_model)
    @token_required("cpe_manage_create")
    def post(self):
        url_logging(logger, g.url)
        args = cpe_manage_args.parse_args(strict=False)
        w = ManageCpe(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w, run_method=w.post, check_method=w.check_params_post, ok_code=200
        )

    @ns.doc(
        description="Discard CPE records.",
        responses=GET_RESPONSES_400_404_409,
        security="Bearer",
    )
    @ns.expect(cpe_manage_model, cpe_manage_args)
    @ns.marshal_with(cpe_manage_response_model)
    @token_required("cpe_manage_delete")
    def delete(self):
        url_logging(logger, g.url)
        args = cpe_manage_args.parse_args(strict=False)
        w = ManageCpe(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w,
            run_method=w.delete,
            check_method=w.check_params_delete,
            ok_code=200,
        )


@with_metadata(PackagesOpenVulns, ns, logger, require_auth=True)
@ns.route(
    "/packages/open_vulns",
    doc={
        "description": (
            "Get a list of all repository packages containing unpatched vulnerabilities"
        ),
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routePackagesOpenVulns(Resource):
    @ns.expect(pkgs_open_vulns_args)
    @ns.marshal_with(pkg_open_vulns)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = pkgs_open_vulns_args.parse_args(strict=True)
        w = PackagesOpenVulns(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/packages/supported_branches",
    doc={
        "description": "Get a list of supported branches.",
        "responses": GET_RESPONSES_404,
        "security": "Bearer",
    },
)
class routePackagesSupportedBranches(Resource):
    # @ns.expect()
    @ns.marshal_with(supported_branches_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = PackagesSupportedBranches(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/packages/maintainer_list",
    doc={
        "description": "Get a list of all maintainers.",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routePackagesMaintainerList(Resource):
    @ns.expect(maintainer_list_args)
    @ns.marshal_with(maintainer_list_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = maintainer_list_args.parse_args(strict=True)
        w = PackagesMaintainerList(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/packages/unmapped",
    doc={
        "description": "Get a list of packages that not mapped to any project.",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routePackagesUnmapped(Resource):
    @ns.expect(pkgs_unmapped_args)
    @ns.marshal_with(pkgs_unmapped_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = pkgs_unmapped_args.parse_args(strict=True)
        w = PackagesUnmapped(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/packages/image_list",
    doc={
        "description": "Get a list of all images.",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routePackagesImageList(Resource):
    @ns.expect(image_list_args)
    @ns.marshal_with(image_list_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = image_list_args.parse_args(strict=True)
        w = PackagesImageList(g.connection, **args)
        return run_worker(worker=w, args=args)


@with_metadata(PncList, ns, logger, require_auth=True)
@ns.route("/pnc/list")
class routePncList(Resource):
    @ns.doc(
        description="Get PNC records list.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(pnc_list_args)
    @ns.marshal_with(pnc_list_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = pnc_list_args.parse_args(strict=True)
        w = PncList(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route("/pnc/manage")
class routeManagePnc(Resource):
    @ns.doc(
        description="Get package to project mapping records.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(pnc_manage_get_args)
    @ns.marshal_with(pnc_manage_get_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = pnc_manage_get_args.parse_args(strict=True)
        w = ManagePnc(g.connection, payload={}, **args)
        return run_worker(worker=w, args=args)

    @ns.doc(
        description="Register new package to project mapping record.",
        responses=RESPONSES_400_409,
        security="Bearer",
    )
    @ns.expect(pnc_manage_model, pnc_manage_args)
    @ns.marshal_with(pnc_manage_response_model)
    @token_required("pnc_manage_create")
    def post(self):
        url_logging(logger, g.url)
        args = pnc_manage_args.parse_args(strict=False)
        w = ManagePnc(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w, run_method=w.post, check_method=w.check_params_post, ok_code=200
        )

    # @ns.doc(
    #     description="Update package to project mapping record.",
    #     responses=RESPONSES_400_404,
    #     security="Bearer",
    # )
    # @ns.expect(pnc_manage_model, pnc_manage_args)
    # @ns.marshal_with(pnc_manage_response_model)
    # @token_required(ldap_groups=[settings.AG.CVE_ADMIN])
    # def put(self):
    #     url_logging(logger, g.url)
    #     args = pnc_manage_args.parse_args(strict=False)
    #     w = ManagePnc(g.connection, payload=ns.payload, **args)
    #     return run_worker(
    #         worker=w, run_method=w.put, check_method=w.check_params_put, ok_code=200
    #     )

    @ns.doc(
        description="Discard package to project mapping record.",
        responses=RESPONSES_400_409,
        security="Bearer",
    )
    @ns.expect(pnc_manage_model, pnc_manage_args)
    @ns.marshal_with(pnc_manage_response_model)
    @token_required("pnc_manage_discard")
    def delete(self):
        url_logging(logger, g.url)
        args = pnc_manage_args.parse_args(strict=False)
        w = ManagePnc(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w,
            run_method=w.delete,
            check_method=w.check_params_delete,
            ok_code=200,
        )


@with_metadata(ListSa, ns, logger, require_auth=True)
@ns.route("/sa/manage")
class routeSaList(Resource):
    @ns.doc(
        description="Get SA errata records list.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(sa_list_args)
    @ns.marshal_with(sa_manage_list_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = sa_list_args.parse_args(strict=True)
        w = ListSa(g.connection, **args)
        return run_worker(worker=w, args=args)

    @ns.doc(
        description="Create SA errata record.",
        responses=RESPONSES_400_409,
        security="Bearer",
    )
    @ns.expect(sa_manage_create_model, sa_manage_args)
    @ns.marshal_with(sa_manage_response_model)
    @token_required("sa_manage_create")
    def post(self):
        url_logging(logger, g.url)
        args = sa_manage_args.parse_args(strict=False)
        w = ManageSa(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w, run_method=w.post, check_method=w.check_params_post, ok_code=200
        )

    @ns.doc(
        description="Update SA errata record.",
        responses=RESPONSES_400_404_409,
        security="Bearer",
    )
    @ns.expect(sa_manage_update_model, sa_manage_args)
    @ns.marshal_with(sa_manage_response_model)
    @token_required("sa_manage_update")
    def put(self):
        url_logging(logger, g.url)
        args = sa_manage_args.parse_args(strict=False)
        w = ManageSa(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w, run_method=w.put, check_method=w.check_params_post, ok_code=200
        )

    @ns.doc(
        description="Discard SA errata record.",
        responses=RESPONSES_400_404_409,
        security="Bearer",
    )
    @ns.expect(sa_manage_discard_model, sa_manage_args)
    @ns.marshal_with(sa_manage_response_model)
    @token_required("sa_manage_discard")
    def delete(self):
        url_logging(logger, g.url)
        args = sa_manage_args.parse_args(strict=False)
        w = ManageSa(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w, run_method=w.delete, check_method=w.check_params_post, ok_code=200
        )


@with_metadata(ChangeHistory, ns, logger, require_auth=True)
@ns.route("/change_history")
class routeChangeHistory(Resource):
    @ns.doc(
        description="Retrieve unified change logs from both Errata and PNC.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(change_history_args)
    @ns.marshal_with(change_history_response_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = change_history_args.parse_args(strict=True)
        w = ChangeHistory(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/comments/list",
    doc={
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeListComments(Resource):
    @ns.doc(
        description="Get comments list.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(comments_list_args)
    @ns.marshal_with(comment_list_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = comments_list_args.parse_args(strict=True)
        w = CommentsList(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/comments",
    doc={
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routePostComment(Resource):
    @ns.doc(
        description="Post a comment.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(comment_manage_create_model)
    @ns.marshal_with(comment_manage_response_model)
    @token_required("comments_create")
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = Comments(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w, run_method=w.post, check_method=w.check_payload, ok_code=200
        )


@ns.route(
    "/comments/<string:id>",
    doc={
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeUpdateAndDiscardComments(Resource):
    @ns.doc(
        description="Discard a comment.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(comment_manage_discard_model)
    @ns.marshal_with(comment_manage_response_model)
    @token_required("comments_discard")
    def delete(self, id):
        url_logging(logger, g.url)
        args = {}
        w = Comments(g.connection, payload=ns.payload, id=id, **args)
        if not w.check_comment_id():
            ns.abort(
                404, message=f"Comment ID '{id}' not found in database", comment_id=id
            )
        return run_worker(
            worker=w, run_method=w.delete, check_method=w.check_payload, ok_code=200
        )

    @ns.doc(
        description="Enable disabled comment.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(comment_manage_update_model)
    @ns.marshal_with(comment_manage_response_model)
    @token_required("comments_enable")
    def put(self, id):
        url_logging(logger, g.url)
        args = {}
        w = Comments(g.connection, payload=ns.payload, id=id, **args)
        if not w.check_comment_id():
            ns.abort(
                404, message=f"Comment ID '{id}' not found in database", comment_id=id
            )
        return run_worker(
            worker=w, run_method=w.put, check_method=w.check_payload, ok_code=200
        )


@with_metadata(DefaultReasonsList, ns, logger, require_auth=True)
@ns.route(
    "/default_reasons/list",
    doc={"responses": GET_RESPONSES_400_404, "security": "Bearer"},
)
class routeListDefaultReasons(Resource):
    @ns.doc(
        description="Get default reasons list.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(default_reasons_list_args)
    @ns.marshal_with(default_reasons_list_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = default_reasons_list_args.parse_args(strict=True)
        w = DefaultReasonsList(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/default_reasons",
    doc={
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeManageDefaultReasons(Resource):
    @ns.doc(
        description="Create a new default reason.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(default_reasons_manage_model)
    @ns.marshal_with(default_reason_response_model)
    @token_required("default_reasons_create")
    def post(self):
        url_logging(logger, g.url)
        w = DefaultReasons(g.connection, payload=ns.payload)
        return run_worker(
            worker=w,
            run_method=w.post,
            check_method=w.check_payload_post,
            ok_code=200,
        )

    @ns.doc(
        description="Enable disabled default reason.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(default_reasons_manage_model)
    @ns.marshal_with(default_reason_response_model)
    @token_required("default_reasons_enable")
    def put(self):
        url_logging(logger, g.url)
        w = DefaultReasons(g.connection, payload=ns.payload)
        return run_worker(
            worker=w,
            run_method=w.put,
            check_method=w.check_payload_put,
            ok_code=200,
        )

    @ns.doc(
        description="Disable enabled default reason.",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(default_reasons_manage_model)
    @ns.marshal_with(default_reason_response_model)
    @token_required("default_reasons_disable")
    def delete(self):
        url_logging(logger, g.url)
        w = DefaultReasons(g.connection, payload=ns.payload)
        return run_worker(
            worker=w,
            run_method=w.delete,
            check_method=w.check_payload_delete,
            ok_code=200,
        )


@with_metadata(VulnStatusList, ns, logger, require_auth=True)
@ns.route(
    "/vuln_status/list",
    doc={
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeManageVulnStatusList(Resource):
    @ns.doc(
        description="List vulnerabilities' statuses",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(vuln_status_list_args)
    @ns.marshal_with(vuln_status_list_response_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = vuln_status_list_args.parse_args(strict=True)
        w = VulnStatusList(g.connection, **args)
        return run_worker(worker=w)


@ns.route("/vuln_status/history")
class routeVulnStatusHistory(Resource):
    @ns.doc(
        description="Get history of vulnerability status",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(vuln_status_history_args)
    @ns.marshal_with(vuln_status_history_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = vuln_status_history_args.parse_args(strict=True)
        w = VulnStatusHistory(g.connection, args=args)
        return run_worker(
            worker=w,
            run_method=w.get,
            check_method=w.check_params_get,
        )


@ns.route("/vuln_status/manage")
class routeManageVulnStatus(Resource):
    @ns.doc(
        description="Get info for vulnerability status",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(vuln_status_manage_args)
    @ns.marshal_with(vuln_status_response_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = vuln_status_manage_args.parse_args(strict=True)
        w = VulnStatus(g.connection, args=args)
        return run_worker(
            worker=w,
            run_method=w.get,
            check_method=w.check_params_get,
        )

    @ns.doc(
        description="Create or update a new vulnerability status",
        responses=RESPONSES_400_404_409 | {201: "Created"},
        security="Bearer",
    )
    @ns.expect(vuln_status_manage_create_model)
    @ns.marshal_with(vuln_status_response_model)
    @token_required("vuln_status_create")
    def post(self):
        url_logging(logger, g.url)
        w = VulnStatus(g.connection, payload=ns.payload)
        return run_worker(
            worker=w,
            run_method=w.post,
            check_method=w.check_params_post,
        )


@ns.route("/vuln_status/select_next")
class routeVulnStatusSelectNext(Resource):
    @ns.doc(
        description="Select next vulnerability for analysis",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(vuln_status_select_next_args)
    @ns.marshal_with(vuln_status_select_next_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = vuln_status_select_next_args.parse_args(strict=True)
        w = VulnStatusSelectNext(g.connection, args=args)
        return run_worker(
            worker=w,
            run_method=w.get,
            check_method=w.check_params_get,
        )


@ns.route("/user/info")
class routeManageErrataUser(Resource):
    @ns.doc(
        description="Get errata user info",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(errata_user_info_args)
    @ns.marshal_with(errata_user_info_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = errata_user_info_args.parse_args(strict=True)
        w = ErrataUserInfo(g.connection, **args)
        return run_worker(worker=w)


@ns.route("/user/last_activities")
class routeManageErrataUserLastActivities(Resource):
    @ns.doc(
        description="Get errata user last activities",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(errata_user_last_activities_args)
    @ns.marshal_with(errata_user_last_activities_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = errata_user_last_activities_args.parse_args(strict=True)
        w = ErrataUserLastActivities(g.connection, **args)
        return run_worker(worker=w)


@ns.route("/user/subscriptions")
class routeManageErrataUserSubscriptions(Resource):
    @ns.doc(
        description="Get errata user subscriptions",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(errata_user_subscriptions_args)
    @ns.marshal_with(errata_user_subscriptions_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = errata_user_subscriptions_args.parse_args(strict=True)
        w = ErrataUserSubscriptions(g.connection, payload=args)
        return run_worker(worker=w)

    @ns.doc(
        description="Create/update errata user subscription",
        responses=POST_RESPONSES_400_404_409,
        security="Bearer",
    )
    @ns.expect(errata_user_subscriptions_request_model)
    @ns.marshal_with(errata_user_subscription_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def post(self):
        url_logging(logger, g.url)
        w = ErrataUserSubscriptions(g.connection, payload=ns.payload)
        return run_worker(worker=w, run_method=w.post, check_method=w.check_params_post)


@ns.route("/user/subscriptions/by_entity")
class routeManageErrataEntitySubscriptions(Resource):
    @ns.doc(
        description="Get errata user subscriptions by entity name",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(errata_entity_subscriptions_args)
    @ns.marshal_with(errata_user_subscriptions_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = errata_entity_subscriptions_args.parse_args(strict=True)
        w = ErrataEntitySubscriptions(g.connection, **args)
        return run_worker(worker=w)


@with_metadata(ErrataUserTracking, ns, logger, require_auth=True)
@ns.route("/user/tracking")
class routeManageErrataUserTrackingList(Resource):
    @ns.doc(
        description="List changes in entities tracked by errata user",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(errata_user_tracking_args)
    @ns.marshal_with(errata_user_tracking_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = errata_user_tracking_args.parse_args(strict=True)
        w = ErrataUserTracking(g.connection, **args)
        return run_worker(worker=w)


@ns.route(
    "/user/tag",
    doc={
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeManageErrataUserTag(Resource):
    @ns.doc(
        description="Lightweight search errata user by nickname for tagging",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(errata_user_tag_args)
    @ns.marshal_with(errata_user_tag_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = errata_user_tag_args.parse_args(strict=True)
        w = ErrataUserTag(g.connection, **args)
        return run_worker(worker=w)


@ns.route("/user/aliases")
class routeManageErrataUserAliases(Resource):
    @ns.doc(
        description="Get errata users aliases",
        responses=GET_RESPONSES_400_404,
        security="Bearer",
    )
    @ns.expect(errata_user_aliases_get_args)
    @ns.marshal_with(errata_user_aliases_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = errata_user_aliases_get_args.parse_args(strict=True)
        w = ErrataUserAliases(g.connection, **args)
        return run_worker(worker=w)

    @ns.doc(
        description="Set errata users aliases",
        responses=RESPONSES_400_409,
        security="Bearer",
    )
    @ns.expect(errata_user_aliases_post_args)
    @token_required("user_aliases_create")
    def post(self):
        url_logging(logger, g.url)
        args = errata_user_aliases_post_args.parse_args(strict=True)
        w = ErrataUserAliases(g.connection, **args)
        return run_worker(worker=w, run_method=w.post, check_method=w.check_params_post)
