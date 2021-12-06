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
from .endpoints.pkgset_info import (
    AllPackagesets,
    PkgsetCategoriesCount,
    AllPackagesetArchs,
)
from .parsers import (
    all_archs_args,
    pkgset_categories_args,
)
from .serializers import (
    all_archs_model,
    all_pkgsets_model,
    pkgset_categories_model,
    all_pkgsets_summary_model,
    pkgsets_summary_status_model,
)

ns = get_namespace()

logger = get_logger(__name__)


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
        "description": ("Get package sets list with source packages count"),
        "responses": {404: "Data not found in database"},
    },
)
class routeAllPackagesetsSourceCount(Resource):
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
class routeAllPackagesetsSummary(Resource):
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
    "/pkgsets_summary_status",
    doc={
        "description": (
            "Get package sets list with source packages count and status info"
        ),
        "responses": {404: "Data not found in database"},
    },
)
class routePackagesetsSummaryStatus(Resource):
    # @ns.expect()
    @ns.marshal_with(pkgsets_summary_status_model)
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
        result, code = wrk.get_summary_status()
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
        "description": ("Get binary package archs list with source packages count"),
        "responses": {
            400: "Request parameters validation error",
            404: "Data not found in database",
        },
    },
)
class routeAllPackagesetArchsSourceCount(Resource):
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
    "/pkgset_categories_count",
    doc={
        "description": (
            "Get list of package categories with count for given package set"
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
