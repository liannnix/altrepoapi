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
from .endpoints.iso_info import AllISOImages, ISOImageInfo
from .parsers import (
    iso_images_args,
)
from .serializers import (
    all_iso_model,
    iso_image_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/iso/all_images",
    doc={
        "description": "Get all ISO images",
        "responses": {404: "Data not found in database"},
    },
)
class routeAllISOImages(Resource):
    # @ns.expect()
    @ns.marshal_with(all_iso_model)
    def get(self):
        args = {}
        url_logging(logger, g.url)
        wrk = AllISOImages(g.connection, **args)
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
    "/iso/info",
    doc={
        "description": "Get branch ISO images info",
        "responses": {
            400: "Request parameters validation error",
            404: "Information not found in database",
        },
    },
)
class routeISOImageInfo(Resource):
    @ns.expect(iso_images_args)
    @ns.marshal_with(iso_image_model)
    def get(self):
        args = iso_images_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = ISOImageInfo(g.connection, **args)
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
