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

from utils import get_logger, url_logging, response_error_parser

from .namespace import get_namespace
from .parsers import package_bugzilla_args, maintainer_bugzilla_args
from .serializers import bugzilla_info_model
from .endpoints.bugzilla_info import Bugzilla

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/bugzilla_by_package",
    doc={
        "description": "Get information from bugzilla by the source package name",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeBugzillaByPackage(Resource):
    @ns.expect(package_bugzilla_args)
    @ns.marshal_list_with(bugzilla_info_model)
    def get(self):
        args = package_bugzilla_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = Bugzilla(g.connection, **args)
        if not wrk.check_params_srcpkg():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get_bug_by_package()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/bugzilla_by_maintainer",
    doc={
        "description": "Get information from bugzilla by the maintainer nickname",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeBugzillaByMaintainer(Resource):
    @ns.expect(maintainer_bugzilla_args)
    @ns.marshal_list_with(bugzilla_info_model)
    def get(self):
        args = maintainer_bugzilla_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = Bugzilla(g.connection, **args)
        if not wrk.check_params_maintainer():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get_bug_by_maintainer()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code
