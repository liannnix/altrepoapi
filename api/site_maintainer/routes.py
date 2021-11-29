# altrepodb API
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

from utils import get_logger, url_logging, response_error_parser

from .namespace import get_namespace
from .endpoints.maintainer import AllMaintainers
from .endpoints.maintainer import MaintainerInfo
from .endpoints.package import MaintainerPackages
from .endpoints.packageset import MaintainerBranches
from .endpoints.repocop import RepocopByMaintainer
from .endpoints.beehive import MaintainerBeehiveErrors
from .parsers import (
    all_maintainers_args,
    maintainer_info_args,
    maintainer_branches_args,
    maintainer_packages_args,
)
from .serializers import (
    all_maintainers_model,
    maintainer_info_model,
    maintainer_pkgs_model,
    maintainer_branches_model,
    repocop_by_maintainer_model,
    beehive_by_maintainer_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/all_maintainers", doc={"description": "alias for /all_maintainers_with_nicknames"}
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
    @ns.expect(maintainer_packages_args)
    @ns.marshal_list_with(maintainer_pkgs_model)
    def get(self):
        args = maintainer_packages_args.parse_args(strict=True)
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
    @ns.expect(maintainer_packages_args)
    @ns.marshal_list_with(repocop_by_maintainer_model)
    def get(self):
        args = maintainer_packages_args.parse_args(strict=True)
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
