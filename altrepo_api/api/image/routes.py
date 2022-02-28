# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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

from platform import release
from flask import g, request
from flask_restx import Resource

from altrepo_api.utils import get_logger, url_logging
from altrepo_api.api.auth.decorators import auth_required
from altrepo_api.api.base import (
    run_worker,
    GET_RESPONSES_404,
    GET_RESPONSES_400_404,
    POST_RESPONSE_400_404,
)
from .endpoints.image_status import ImageStatus, ImageTagStatus

from .namespace import get_namespace
from .endpoints.iso_info import AllISOImages, ISOImageInfo
from .endpoints.packages import CheckPackages
from .parsers import (
    iso_images_args,
    image_tag_args,
)
from .serializers import (
    all_iso_model,
    iso_image_model,
    pkgs_json_model,
    pkg_inspect_sp_model,
    pkg_inspect_regular_model,
    image_status_get_model,
    img_json_model,
    img_tag_status_get_model,
    img_tag_json_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/iso/all_images",
    doc={
        "description": "Get all ISO images",
        "responses": GET_RESPONSES_404,
    },
)
class routeAllISOImages(Resource):
    # @ns.expect()
    @ns.marshal_with(all_iso_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = AllISOImages(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/iso/info",
    doc={
        "description": "Get branch ISO images info",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeISOImageInfo(Resource):
    @ns.expect(iso_images_args)
    @ns.marshal_with(iso_image_model)
    def get(self):
        url_logging(logger, g.url)
        args = iso_images_args.parse_args(strict=True)
        w = ISOImageInfo(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/inspect/regular",
    doc={
        "description": "Inspect binary packages from regular distribution image",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeCheckPackagesRegular(Resource):
    @ns.expect(pkgs_json_model)
    @ns.marshal_with(pkg_inspect_regular_model)
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = CheckPackages(g.connection, payload=ns.payload, **args)
        return run_worker(worker=w, args=args, run_method=w.post_regular)


@ns.route(
    "/inspect/sp",
    doc={
        "description": "Inspect binary packages from SP distribution image",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeCheckPackagesSP(Resource):
    @ns.expect(pkgs_json_model)
    @ns.marshal_with(pkg_inspect_sp_model)
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = CheckPackages(g.connection, payload=ns.payload, **args)
        return run_worker(worker=w, args=args, run_method=w.post_sp)


@ns.route("/image_status")
class routeImageStatus(Resource):
    @ns.doc(
        description="Load image status into database",
        responses=POST_RESPONSE_400_404,
    )
    @ns.expect(img_json_model)
    @ns.doc(security="BasicAuth")
    @auth_required
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = ImageStatus(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w,
            run_method=w.post,
            check_method=w.check_params_post,
            args=args,
            ok_code=201,
        )

    @ns.doc(
        description="Get image status into database",
        responses=GET_RESPONSES_400_404,
    )
    @ns.marshal_with(image_status_get_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = ImageStatus(g.connection, payload=ns.payload, **args)
        return run_worker(worker=w, args=args, run_method=w.get)


@ns.route("/image_tag_status")
class routeImageTagStatus(Resource):
    @ns.doc(
        description="Load iso image status into database",
        responses=POST_RESPONSE_400_404,
    )
    @ns.expect(img_tag_json_model)
    @ns.doc(security="BasicAuth")
    @auth_required
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = ImageTagStatus(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w,
            run_method=w.post,
            args=args,
            ok_code=201,
        )

    @ns.doc(
        description="Get iso image status into database",
        responses=GET_RESPONSES_400_404,
    )
    @ns.expect(image_tag_args)
    @ns.marshal_with(img_tag_status_get_model)
    def get(self):
        url_logging(logger, g.url)
        args = image_tag_args.parse_args(strict=True)
        w = ImageTagStatus(g.connection, payload=ns.payload, **args)
        return run_worker(
            worker=w,
            args=args,
            check_method=w.check_params_get,
            run_method=w.get
        )
