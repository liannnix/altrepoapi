# ALTRepo API
# Copyright (C) 2021  BaseALT Ltd

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
from flask_restx import Resource, abort

from altrepo_api.utils import get_logger, url_logging, response_error_parser

from .namespace import get_namespace
from .endpoints.find_package import PackagesetFindPackages, FastPackagesSearchLookup
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
    pkgs_search_by_name_args,
)
from .serializers import (
    pkgset_packages_model,
    pkgset_pkghash_model,
    fing_pkgs_by_name_model,
    pkgsets_by_hash_model,
    last_packages_branch_model,
    fast_pkgs_search_model,
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
    "/fast_packages_search_lookup",
    doc={
        "description": "Fast packages search by name",
        "responses": {
            400: "Request parameters validation error",
            404: "Data not found in database",
        },
    },
)
class routePackagesetFastPackagesSearch(Resource):
    @ns.expect(pkgs_search_by_name_args)
    @ns.marshal_with(fast_pkgs_search_model)
    def get(self):
        args = pkgs_by_name_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = FastPackagesSearchLookup(g.connection, **args)
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
