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

from flask import g
from flask_restx import Resource

from altrepo_api.utils import get_logger, url_logging
from altrepo_api.api.base import run_worker, GET_RESPONSES_400_404

from .namespace import get_namespace
from .endpoints.dependecy_info import (
    DependsBinPackage,
    PackagesDependence,
    DependsSrcPackage,
)
from .endpoints.backport_helper import BackportHelper
from .parsers import pkgs_depends_args, src_pkg_depends_args, backport_helper_args
from .serializers import (
    package_dependencies_model,
    depends_packages_model,
    package_build_deps_model,
    backport_helper_model
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/binary_package_dependencies/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get binary package dependencies",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeDependsBinPackage(Resource):
    @ns.expect()
    @ns.marshal_with(package_dependencies_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = {}
        w = DependsBinPackage(g.connection, pkghash)
        return run_worker(worker=w, args=args)


@ns.route(
    "/packages_by_dependency",
    doc={
        "description": "Get binary packages by dependency name and type",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageDepends(Resource):
    @ns.expect(pkgs_depends_args)
    @ns.marshal_with(depends_packages_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgs_depends_args.parse_args(strict=True)
        w = PackagesDependence(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/source_package_dependencies/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get source package build dependencies",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeDependsSrcPackage(Resource):
    @ns.expect(src_pkg_depends_args)
    @ns.marshal_with(package_build_deps_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = src_pkg_depends_args.parse_args(strict=True)
        w = DependsSrcPackage(g.connection, pkghash, **args)
        return run_worker(worker=w, args=args)


@ns.route("/backport_helper")
@ns.doc(
    description="Find packages required to backport too",
    responses=GET_RESPONSES_400_404,
)
class routeAclByPackages(Resource):
    @ns.expect(backport_helper_args)
    @ns.marshal_list_with(backport_helper_model)
    def get(self):
        url_logging(logger, g.url)
        args = backport_helper_args.parse_args(strict=True)
        w = BackportHelper(g.connection, **args)
        return run_worker(worker=w, args=args)
