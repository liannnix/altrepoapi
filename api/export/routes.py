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
from .endpoints.repology import RepologyExport

from .parsers import *
from .serializers import repology_export_model

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/repology/<string:branch>",
    doc={
        "params": {"branch": "branch name"},
        "description": "Get branch info export for Repology",
        "responses": {
            400: "Request parameters validation error",
            404: "Information not found in database",
        },
    },
)
class routePackageInfo(Resource):
    # @ns.expect(xxx_args)
    @ns.marshal_with(repology_export_model)
    def get(self, branch):
        # args = xxx_args.parse_args(strict=True)
        args = {}
        url_logging(logger, g.url)
        wrk = RepologyExport(g.connection, branch, **args)
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
