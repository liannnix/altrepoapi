from flask import g
from flask_restx import Resource, abort

from utils import get_logger, url_logging, response_error_parser

from .namespace import get_namespace
from .endpoints.find_package import PackagesetFindPackages
from .endpoints.package_hash import (
    PackagesetPackageHash,
    PackagesetPackageBinaryHash,
)
from .endpoints.pkgset_packages import (
    PackagesetPackages,
    AllPackagesetsByHash,
    LastBranchPackages,
)
from .parsers import (
    pkgs_by_name_args,
    pkgset_pkghash_args,
    pkgset_packages_args,
    last_pkgs_branch_args,
    pkgset_pkg_binary_hash_args,
)
from .serializers import (
    pkgset_packages_model,
    pkgset_pkghash_model,
    fing_pkgs_by_name_model,
    pkgsets_by_hash_model,
    last_packages_branch_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/repository_packages",
    doc={
        "description": (
            "Get list of packageset packages in accordance to given parameters"
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
    "/pkghash_by_name",
    doc={
        "description": (
            "Get source package hash by package name and package set name"
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
            "Get source package hash by package name and package set name"
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
    "/last_packages_by_branch",
    doc={
        "description": ("Get list of last packages from branch for given parameters"),
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeLastBranchPackages(Resource):
    @ns.expect(last_pkgs_branch_args)
    @ns.marshal_with(last_packages_branch_model)
    def get(self):
        args = last_pkgs_branch_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = LastBranchPackages(g.connection, **args)
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
