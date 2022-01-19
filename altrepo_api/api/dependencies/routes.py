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
from .endpoints.dependecy_info import (
    DependsBinPackage,
    PackagesDependence,
    DependsSrcPackage,
)
from .parsers import pkgs_depends_args, src_pkg_depends_args
from .serializers import (
    package_dependencies_model,
    depends_packages_model,
    package_build_deps_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/binary_package_dependencies/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get binary package dependencies",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeDependsBinPakage(Resource):
    @ns.expect()
    @ns.marshal_with(package_dependencies_model)
    def get(self, pkghash):
        args = {}
        url_logging(logger, g.url)
        wrk = DependsBinPackage(g.connection, pkghash)
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
    "/packages_by_dependency",
    doc={
        "description": "Get binary packages by dependency name and type",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackageDepends(Resource):
    @ns.expect(pkgs_depends_args)
    @ns.marshal_with(depends_packages_model)
    def get(self):
        args = pkgs_depends_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackagesDependence(g.connection, **args)
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
    "/source_package_dependencies/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get source package build dependencies",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeDependsSrcPackage(Resource):
    @ns.expect(src_pkg_depends_args)
    @ns.marshal_with(package_build_deps_model)
    def get(self, pkghash):
        args = src_pkg_depends_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = DependsSrcPackage(g.connection, pkghash, **args)
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
