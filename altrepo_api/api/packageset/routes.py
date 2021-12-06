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

from flask import g, request
from flask_restx import Resource, abort, Namespace

from altrepo_api.utils import get_logger, url_logging, response_error_parser
from altrepo_api.api.auth.decorators import auth_required

from .endpoints.pkgset_compare import PackagesetCompare
from .endpoints.pkgset_packages import PackagesetPackages
from .endpoints.pkgset_status import RepositoryStatus, ActivePackagesets

from .namespace import get_namespace
from .parsers import pkgset_compare_args, pkgset_packages_args
from .serializers import (
    pkgset_compare_model,
    pkgset_packages_model,
    pkgset_status_post_model,
    pkgset_status_get_model,
    active_pkgsets_model,
)

ns = get_namespace()

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
    "/compare_packagesets",
    doc={
        "description": "Get difference list of packages from two package sets",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackagesetCompare(Resource):
    @ns.expect(pkgset_compare_args)
    @ns.marshal_with(pkgset_compare_model)
    def get(self):
        args = pkgset_compare_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackagesetCompare(g.connection, **args)
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


@ns.route("/pkgset_status")
class routeRepositoryStatus(Resource):
    @ns.doc(
        description="Load package set status into database",
        responses={
            201: "Data loaded",
            400: "Request parameters validation error",
            404: "Requested data not found in database",
        },
    )
    @ns.expect(pkgset_status_post_model)
    @ns.doc(security="BasicAuth")
    @auth_required
    def post(self):
        args = {}
        url_logging(logger, g.url)
        wrk = RepositoryStatus(g.connection, json_data=request.json)
        if not wrk.check_params_post():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.post()
        if code != 201:
            abort(code, **response_error_parser(result))
        return result, code

    @ns.doc(
        description="Get package set status into database",
        responses={
            400: "Request parameters validation error",
            404: "Requested data not found in database",
        },
    )
    @ns.marshal_with(pkgset_status_get_model)
    def get(self):
        args = {}
        url_logging(logger, g.url)
        wrk = RepositoryStatus(g.connection, json_data=request.json)
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
    "/active_packagesets",
    doc={
        "description": ("Get list of active package sets"),
        "responses": {
            404: "Package sets not found in database",
        },
    },
)
class routeActivePackagesets(Resource):
    # @ns.expect()
    @ns.marshal_with(active_pkgsets_model)
    def get(self):
        args = {}
        url_logging(logger, g.url)
        wrk = ActivePackagesets(g.connection, **args)
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
