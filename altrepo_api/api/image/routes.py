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
from altrepo_api.api.auth.decorators import auth_required
from altrepo_api.api.base import (
    run_worker,
    GET_RESPONSES_404,
    GET_RESPONSES_400_404,
    POST_RESPONSES_400_404,
)
from .endpoints.find_image_by_package import FindImagesByPackageName
from .endpoints.image_status import ImageStatus, ImageTagStatus, ActiveImages

from .namespace import get_namespace
from .endpoints.image_info import (
    AllISOImages,
    ImageInfo,
    LastImagePackages,
    ImageTagUUID,
    ImageCategoriesCount,
    ImagePackages,
)
from .endpoints.packages import CheckPackages
from .parsers import (
    image_info_args,
    image_tag_args,
    image_last_packages_args,
    image_uuid_args,
    image_categories_args,
    image_packages_args,
    active_images_args,
    find_images_args,
)
from .serializers import (
    all_iso_model,
    image_info_model,
    pkgs_json_model,
    pkg_inspect_sp_model,
    pkg_inspect_regular_model,
    image_status_get_model,
    img_json_model,
    img_tag_status_get_model,
    img_tag_json_model,
    packages_image_model,
    image_tag_uuid_model,
    image_categories_model,
    last_packages_image_model,
    active_images_model,
    find_images_by_pkg_model,
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
    "/image_info",
    doc={
        "description": "Get branch images info",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeImageInfo(Resource):
    @ns.expect(image_info_args)
    @ns.marshal_with(image_info_model)
    def get(self):
        url_logging(logger, g.url)
        args = image_info_args.parse_args(strict=True)
        w = ImageInfo(g.connection, **args)
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
        responses=POST_RESPONSES_400_404,
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
        w = ImageStatus(g.connection, payload=None, **args)
        return run_worker(worker=w, args=args, run_method=w.get)


@ns.route("/image_tag_status")
class routeImageTagStatus(Resource):
    @ns.doc(
        description="Load iso image status into database",
        responses=POST_RESPONSES_400_404,
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
        args = image_tag_args.parse_args(strict=False)
        w = ImageTagStatus(g.connection, payload=None, **args)
        return run_worker(
            worker=w, args=args, check_method=w.check_params_get, run_method=w.get
        )


@ns.route(
    "/last_packages_by_image",
    doc={
        "description": "Get list of last packages from image for given parameters",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeLastImagePackages(Resource):
    @ns.expect(image_last_packages_args)
    @ns.marshal_with(last_packages_image_model)
    def get(self):
        url_logging(logger, g.url)
        args = image_last_packages_args.parse_args(strict=True)
        w = LastImagePackages(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/image_uuid_by_tag",
    doc={
        "description": "Get image UUID by image tag",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeImageTagUuid(Resource):
    @ns.expect(image_uuid_args)
    @ns.marshal_with(image_tag_uuid_model)
    def get(self):
        url_logging(logger, g.url)
        args = image_uuid_args.parse_args(strict=True)
        w = ImageTagUUID(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/image_categories_count",
    doc={
        "description": ("Get list of package categories with count for image"),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeImageCategoriesCount(Resource):
    @ns.expect(image_categories_args)
    @ns.marshal_with(image_categories_model)
    def get(self):
        url_logging(logger, g.url)
        args = image_categories_args.parse_args(strict=True)
        w = ImageCategoriesCount(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/image_packages",
    doc={
        "description": ("Get list of image packages in accordance to given parameters"),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeImagePackages(Resource):
    @ns.expect(image_packages_args)
    @ns.marshal_with(packages_image_model)
    def get(self):
        url_logging(logger, g.url)
        args = image_packages_args.parse_args(strict=True)
        w = ImagePackages(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/last_packages_image_with_cve_fixed",
    doc={
        "description": (
            "Get information about last packages with CVE "
            "fixes mentioned in changelog for given image"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeLastImagePackagesWithCveFix(Resource):
    @ns.expect(image_last_packages_args)
    @ns.marshal_with(last_packages_image_model)
    def get(self):
        url_logging(logger, g.url)
        args = image_last_packages_args.parse_args(strict=True)
        w = LastImagePackages(g.connection, is_cve=True, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/active_images",
    doc={
        "description": ("Get active images for a given repository"),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeActiveImages(Resource):
    @ns.expect(active_images_args)
    @ns.marshal_with(active_images_model)
    def get(self):
        url_logging(logger, g.url)
        args = active_images_args.parse_args(strict=True)
        w = ActiveImages(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/find_images_by_package_name",
    doc={
        "description": (
            "Get images by package name for a given repository and edition"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeFindImagesByPackage(Resource):
    @ns.expect(find_images_args)
    @ns.marshal_with(find_images_by_pkg_model)
    def get(self):
        url_logging(logger, g.url)
        args = find_images_args.parse_args(strict=True)
        w = FindImagesByPackageName(g.connection, **args)
        return run_worker(worker=w, args=args)
