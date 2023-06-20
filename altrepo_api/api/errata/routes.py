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
from flask_restx import Resource, abort

from altrepo_api.api.base import (
    GET_RESPONSES_400_404,
    GET_RESPONSES_404,
    POST_RESPONSES_400_404,
    run_worker,
)
from altrepo_api.utils import (
    get_logger,
    response_error_parser,
    send_file_compat,
    url_logging,
)

from .endpoints.main import BranchesUpdates, PackagesUpdates, Search
from .endpoints.oval import OvalBranches, OvalExport
from .namespace import get_namespace
from .parsers import (
    errata_search_args,
    oval_export_args,
)
from .serializers import (
    erratas_ids_json_list_model,
    erratas_model,
    errata_branches_updates_model,
    errata_packages_updates_model,
    oval_branches_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/export/oval/branches",
    doc={
        "description": "Get branches with OVAL definitions export available",
        "responses": GET_RESPONSES_404,
    },
)
class routePackageSetBinaries(Resource):
    # @ns.expect(xxx_args)
    @ns.marshal_with(oval_branches_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = OvalBranches(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/export/oval/<string:branch>",
    doc={
        "description": "Get OVAL definitions of closed issues of branch packages",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeOvalExport(Resource):
    @ns.expect(oval_export_args)
    @ns.produces(["application/zip"])
    def get(self, branch):
        url_logging(logger, g.url)
        args = oval_export_args.parse_args(strict=True)
        w = OvalExport(g.connection, branch, **args)
        if not w.check_params():
            abort(
                400,  # type: ignore
                message="Request parameters validation error",
                args=args,
                validation_message=w.validation_results,
            )
        result, code = w.get()
        if code != 200:
            abort(code, **response_error_parser(result))  # type: ignore
        file = result["file"]
        file_name = result["file_name"]
        file.seek(0)
        return send_file_compat(
            file=file,
            as_attachment=True,
            mimetype="application/zip",
            attachment_filename=file_name,
        )


@ns.route(
    "/packages_updates",
    doc={
        "description": "Get information about packages updates",
        "responses": POST_RESPONSES_400_404,
    },
)
class routePackagesUpdates(Resource):
    @ns.expect(erratas_ids_json_list_model)
    @ns.marshal_with(errata_packages_updates_model)
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = PackagesUpdates(g.connection, json_data=ns.payload)
        return run_worker(worker=w, args=args, run_method=w.post, ok_code=200)


@ns.route(
    "/branches_updates",
    doc={
        "description": "Get information about branches updates",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeBranchesUpdates(Resource):
    @ns.expect(erratas_ids_json_list_model)
    @ns.marshal_with(errata_branches_updates_model)
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = BranchesUpdates(g.connection, json_data=ns.payload)
        return run_worker(worker=w, args=args, run_method=w.post, ok_code=200)


@ns.route(
    "/search",
    doc={
        "description": "Find corresponding erratas",
        "responses": GET_RESPONSES_404,
    },
)
class routeSearch(Resource):
    @ns.expect(errata_search_args)
    @ns.marshal_with(erratas_model)
    def get(self):
        url_logging(logger, g.url)
        args = errata_search_args.parse_args(strict=False)
        w = Search(g.connection, **args)
        return run_worker(worker=w, args=args)
