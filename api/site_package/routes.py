from flask import g
from flask_restx import Resource, abort

from utils import get_logger, url_logging, response_error_parser

from .namespace import get_namespace
from .endpoints.package_info import (
    PackageInfo,
    DeletedPackageInfo,
    PackagesBinaryListInfo,
)
from .endpoints.changelog import PackageChangelog
from .endpoints.downloads import PackageDownloadLinks, BinaryPackageDownloadLinks
from .endpoints.versions import SourcePackageVersions, PackageVersions
from .endpoints.scripts import BinaryPackageScripts
from .endpoints.cve import LastPackagesWithCVEFix
from .parsers import (
    src_downloads_args,
    bin_downloads_args,
    package_chlog_args,
    package_info_args,
    pkgs_with_cve_fix_args,
    pkgs_binary_list_args,
    deleted_package_args,
    src_pkgs_versions_args,
    pkgs_versions_args,
)
from .serializers import (
    package_chlog_model,
    package_info_model,
    deleted_package_model,
    last_pkgs_with_cve_fix_model,
    package_downloads_model,
    pkgs_binary_list_model,
    depends_packages_model,
    src_pkgs_versions_model,
)

ns = get_namespace()

logger = get_logger(__name__)


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
    "/binary_package_archs_and_versions",
    doc={
        "description": "Get binary package archs and versions",
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
    @ns.expect(deleted_package_args)
    @ns.marshal_with(deleted_package_model)
    def get(self):
        args = deleted_package_args.parse_args(strict=True)
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
    "/binary_package_scripts/<int:pkghash>",
    doc={
        "description": "Get binary package scripts",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeBinPackageScripts(Resource):
    # @ns.expect()
    @ns.marshal_with(depends_packages_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        wrk = BinaryPackageScripts(g.connection, pkghash)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                # args=args,
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
    "/package_downloads/<int:pkghash>",
    "/package_downloads_src/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get package download links by source package hash",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackageDownloadLinks(Resource):
    pass

    @ns.expect(src_downloads_args)
    @ns.marshal_with(package_downloads_model)
    def get(self, pkghash):
        args = src_downloads_args.parse_args(strict=True)
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


@ns.route(
    "/package_downloads_bin/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get binary package download link",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeBinaryPackageDownloadLinks(Resource):
    pass

    @ns.expect(bin_downloads_args)
    @ns.marshal_with(package_downloads_model)
    def get(self, pkghash):
        args = bin_downloads_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = BinaryPackageDownloadLinks(g.connection, pkghash, **args)
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
    "/source_package_versions",
    doc={
        "description": "Get source package versions from last branches",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeSourcePackageVersions(Resource):
    @ns.expect(src_pkgs_versions_args)
    @ns.marshal_with(src_pkgs_versions_model)
    def get(self):
        args = src_pkgs_versions_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = SourcePackageVersions(g.connection, **args)
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
    "/package_versions",
    doc={
        "description": "Get source or binary package versions from last branches",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackageVersions(Resource):
    @ns.expect(pkgs_versions_args)
    @ns.marshal_with(src_pkgs_versions_model)
    def get(self):
        args = pkgs_versions_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageVersions(g.connection, **args)
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
