# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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
from .endpoints.versions import PackageVersionsFromImages
from .parsers import pkgs_versions_from_images_args
from .serializers import pkgs_versions_from_images_model


ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/package_versions_from_images",
    doc={
        "description": "Get binary packages versions from images",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageVersionsFromImages(Resource):
    @ns.expect(pkgs_versions_from_images_args)
    @ns.marshal_with(pkgs_versions_from_images_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgs_versions_from_images_args.parse_args(strict=True)
        w = PackageVersionsFromImages(g.connection, **args)
        return run_worker(worker=w, args=args)
