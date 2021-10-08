from flask import g
from flask_restx import Resource, abort, Namespace

from utils import get_logger, url_logging, response_error_parser

from .endpoints.package_info import PackageInfo, PackageChangelog, DeletedPackageInfo, PackagesBinaryListInfo
from .endpoints.package_info import LastPackagesWithCVEFix, PackageDownloadLinks
from .endpoints.pkgset_packages import PackagesetPackages, PackagesetPackageHash, PackagesetPackageBinaryHash
from .endpoints.packager_info import AllMaintainers, MaintainerInfo, MaintainerPackages
from .endpoints.packager_info import MaintainerBranches, RepocopByMaintainer
from .endpoints.packager_info import MaintainerBeehiveErrors
from .endpoints.pkgset_packages import PackagesetFindPackages, AllPackagesets
from .endpoints.pkgset_packages import PkgsetCategoriesCount, AllPackagesetArchs
from .endpoints.pkgset_packages import AllPackagesetsByHash
from .endpoints.task_info import TasksByPackage, LastTaskPackages, TasksByMaintainer

ns = Namespace("site", description="web site API")

from .parsers import (
    pkgset_packages_args,
    package_chlog_args,
    package_info_args,
    all_maintainers_args,
    maintainer_info_args,
    maintainer_branches_args,
    pkgset_pkghash_args,
    task_by_name_args,
    pkgs_by_name_args,
    last_pkgs_args,
    pkgset_categories_args,
    all_archs_args,
    pkgs_with_cve_fix_args,
    pkgset_pkg_binary_hash_args,
    pkgs_binary_list_args,
)
from .serializers import (
    pkgset_packages_model,
    package_chlog_model,
    package_info_model,
    all_maintainers_model,
    maintainer_info_model,
    maintainer_pkgs_model,
    maintainer_branches_model,
    repocop_by_maintainer_model,
    all_pkgsets_model,
    all_archs_model,
    pkgset_categories_model,
    pkgset_pkghash_model,
    task_by_name_model,
    fing_pkgs_by_name_model,
    pkgsets_by_hash_model,
    last_packages_model,
    deleted_package_model,
    last_pkgs_with_cve_fix_model,
    all_pkgsets_summary_model,
    beehive_by_maintainer_model,
    package_downloads_model,
    pkgs_binary_list_model,
)

logger = get_logger(__name__)


@ns.route(
    "/repository_packages",
    doc={
        "description": (
            "Get list of packageset packages in accordance " "to given parameters"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackagesetPackages(Resource):
    @ns.expect(pkgset_packages_args)
    @ns.marshal_with(pkgset_packages_model)
    def get(self):
        args = pkgset_packages_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackagesetPackages(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/package_changelog/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get package changelog history by hash",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackageChangelog(Resource):
    pass

    @ns.expect(package_chlog_args)
    @ns.marshal_with(package_chlog_model)
    def get(self, pkghash):
        args = package_chlog_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageChangelog(g.connection, pkghash, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/package_info/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get package info by hash",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackageInfo(Resource):
    pass

    @ns.expect(package_info_args)
    @ns.marshal_with(package_info_model)
    def get(self, pkghash):
        args = package_info_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageInfo(g.connection, pkghash, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/packages_binary_list",
    doc={
        "description": "Get package info by hash",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackagesBinaryList(Resource):
    @ns.expect(pkgs_binary_list_args)
    @ns.marshal_with(pkgs_binary_list_model)
    def get(self):
        args = pkgs_binary_list_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackagesBinaryListInfo(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/pkghash_by_name",
    doc={
        "description": (
            "Get source package hash by package name and " "package set name"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackagesetPackageHash(Resource):
    @ns.expect(pkgset_pkghash_args)
    @ns.marshal_with(pkgset_pkghash_model)
    def get(self):
        args = pkgset_pkghash_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackagesetPackageHash(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code

@ns.route(
    "/pkghash_by_binary_name",
    doc={
        "description": (
            "Get source package hash by package name and " "package set name"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackagesetPackageBinaryHash(Resource):
    @ns.expect(pkgset_pkg_binary_hash_args)
    @ns.marshal_with(pkgset_pkghash_model)
    def get(self):
        args = pkgset_pkg_binary_hash_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackagesetPackageBinaryHash(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/tasks_by_package",
    doc={
        "description": "Get tasks list by source package name",
        "responses": {
            400: "Request parameters validation error",
            404: "Data not found in database",
        },
    },
)
class routeTasksByPackage(Resource):
    @ns.expect(task_by_name_args)
    @ns.marshal_with(task_by_name_model)
    def get(self):
        args = task_by_name_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = TasksByPackage(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/find_packages",
    doc={
        "description": "Find packages by name",
        "responses": {
            400: "Request parameters validation error",
            404: "Data not found in database",
        },
    },
)
class routePackagesetFindPackages(Resource):
    @ns.expect(pkgs_by_name_args)
    @ns.marshal_with(fing_pkgs_by_name_model)
    def get(self):
        args = pkgs_by_name_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackagesetFindPackages(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/all_pkgsets",
    doc={
        "description": "Get package sets list",
        "responses": {404: "Data not found in database"},
    },
)
class routeAllPackagesets(Resource):
    # @ns.expect()
    @ns.marshal_with(all_pkgsets_model)
    def get(self):
        args = {}
        url_logging(logger, g.url)
        wrk = AllPackagesets(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/all_pkgsets_with_src_count",
    doc={
        "description": ("Get package sets list " "with source packages count"),
        "responses": {404: "Data not found in database"},
    },
)
class routeAllPackagesets(Resource):
    # @ns.expect()
    @ns.marshal_with(all_pkgsets_model)
    def get(self):
        args = {}
        url_logging(logger, g.url)
        wrk = AllPackagesets(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get_with_pkgs_count()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/all_pkgsets_summary",
    doc={
        "description": "Get package sets list with source packages count",
        "responses": {404: "Data not found in database"},
    },
)
class routeAllPackagesets(Resource):
    # @ns.expect()
    @ns.marshal_with(all_pkgsets_summary_model)
    def get(self):
        args = {}
        url_logging(logger, g.url)
        wrk = AllPackagesets(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get_summary()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/all_pkgset_archs",
    doc={
        "description": "Get binary package archs list",
        "responses": {
            400: "Request parameters validation error",
            404: "Data not found in database",
        },
    },
)
class routeAllPackagesetArchs(Resource):
    @ns.expect(all_archs_args)
    @ns.marshal_with(all_archs_model)
    def get(self):
        args = all_archs_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = AllPackagesetArchs(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/all_pkgset_archs_with_src_count",
    doc={
        "description": ("Get binary package archs list " "with source packages count"),
        "responses": {
            400: "Request parameters validation error",
            404: "Data not found in database",
        },
    },
)
class routeAllPackagesetArchs(Resource):
    @ns.expect(all_archs_args)
    @ns.marshal_with(all_archs_model)
    def get(self):
        args = all_archs_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = AllPackagesetArchs(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get_with_src_count()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/last_packages",
    doc={
        "description": ("Get list of last packages from tasks " "for given parameters"),
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeLastTaskPackages(Resource):
    @ns.expect(last_pkgs_args)
    @ns.marshal_with(last_packages_model)
    def get(self):
        args = last_pkgs_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = LastTaskPackages(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/pkgset_categories_count",
    doc={
        "description": (
            "Get list of package categories with count " "for given package set"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePkgsetCategoriesCount(Resource):
    @ns.expect(pkgset_categories_args)
    @ns.marshal_with(pkgset_categories_model)
    def get(self):
        args = pkgset_categories_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PkgsetCategoriesCount(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/packagesets_by_hash/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get package set list by package hash",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackagsetsByHash(Resource):
    pass

    @ns.expect()
    @ns.marshal_with(pkgsets_by_hash_model)
    def get(self, pkghash):
        args = {}
        url_logging(logger, g.url)
        wrk = AllPackagesetsByHash(g.connection, pkghash, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/all_maintainers",
    doc={"description": "alias for /all_maintainers_with_nicknames"}
)
@ns.route("/all_maintainers_with_nicknames")
@ns.doc(
    description="List of maintainers in branch with nicknames and source packages count",
    responses={
        400: "Request parameters validation error",
        404: "Package not found in database",
    },
)
class routeMaintainersAll(Resource):
    @ns.expect(all_maintainers_args)
    @ns.marshal_list_with(all_maintainers_model)
    def get(self):
        args = all_maintainers_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = AllMaintainers(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/maintainer_info",
    doc={
        "description": "Maintainer information",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeMaintainersInfo(Resource):
    @ns.expect(maintainer_info_args)
    @ns.marshal_list_with(maintainer_info_model)
    def get(self):
        args = maintainer_info_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = MaintainerInfo(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/maintainer_packages",
    doc={
        "description": "Packages collected by the specified maintainer",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeMaintainerPackages(Resource):
    @ns.expect(maintainer_info_args)
    @ns.marshal_list_with(maintainer_pkgs_model)
    def get(self):
        args = maintainer_info_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = MaintainerPackages(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/maintainer_branches",
    doc={
        "description": "Packages collected by the specified maintainer",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeMaintainerBranches(Resource):
    @ns.expect(maintainer_branches_args)
    @ns.marshal_list_with(maintainer_branches_model)
    def get(self):
        args = maintainer_branches_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = MaintainerBranches(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/tasks_by_maintainer",
    doc={
        "description": "Get tasks list by maintainer nickname",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeTasksByMaintainer(Resource):
    @ns.expect(maintainer_info_args)
    @ns.marshal_list_with(task_by_name_model)
    def get(self):
        args = maintainer_info_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = TasksByMaintainer(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/repocop_by_maintainer",
    doc={
        "description": "Get repocop results by the maintainers nickname",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeRepocopByMaintainer(Resource):
    @ns.expect(maintainer_info_args)
    @ns.marshal_list_with(repocop_by_maintainer_model)
    def get(self):
        args = maintainer_info_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = RepocopByMaintainer(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/deleted_package_info",
    doc={
        "description": ("Get information about package deleted from branch"),
        "responses": {
            400: "Request parameters validation error",
            404: "Package deletion info not found in database",
        },
    },
)
class routeDeletedPackageInfo(Resource):
    @ns.expect(pkgset_pkghash_args)
    @ns.marshal_with(deleted_package_model)
    def get(self):
        args = pkgset_pkghash_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = DeletedPackageInfo(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/last_packages_with_cve_fixed",
    doc={
        "description": (
            "Get information about last packages with CVE "
            "fixes mentioned in changelog"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Package deletion info not found in database",
        },
    },
)
class routeLastPackagesWithCVEFix(Resource):
    @ns.expect(pkgs_with_cve_fix_args)
    @ns.marshal_with(last_pkgs_with_cve_fix_model)
    def get(self):
        args = pkgs_with_cve_fix_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = LastPackagesWithCVEFix(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/beehive_errors_by_maintainer",
    doc={
        "description": "Get Beehive rebuild errors by the maintainer's nickname",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeBeehiveByMaintainer(Resource):
    @ns.expect(maintainer_info_args)
    @ns.marshal_list_with(beehive_by_maintainer_model)
    def get(self):
        args = maintainer_info_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = MaintainerBeehiveErrors(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/package_downloads/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get package download links by hash",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackageDownloadLinks(Resource):
    pass

    @ns.expect(all_archs_args)
    @ns.marshal_with(package_downloads_model)
    def get(self, pkghash):
        args = all_archs_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageDownloadLinks(g.connection, pkghash, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code
