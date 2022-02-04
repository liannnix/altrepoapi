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

from flask import g
from flask_restx import Resource

from altrepo_api.utils import get_logger, url_logging
from altrepo_api.api.base import run_worker, GET_RESPONSES_400_404

from .namespace import get_namespace
from .endpoints.repology import RepologyExport
from .endpoints.sitemap import SitemapPackages
from .endpoints.packageset import PackageSetBinaries

from .parsers import pkgset_packages_args
from .serializers import (
    repology_export_model,
    sitemap_packages_export_model,
    pkgset_packages_export_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/repology/<string:branch>",
    doc={
        "params": {"branch": "branch name"},
        "description": "Get branch info export for Repology",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageInfo(Resource):
    # @ns.expect(xxx_args)
    @ns.marshal_with(repology_export_model)
    def get(self, branch):
        url_logging(logger, g.url)
        args = {}
        w = RepologyExport(g.connection, branch, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/sitemap_packages/<string:branch>",
    doc={
        "params": {"branch": "branch name"},
        "description": "Get branch source packages for sitemap",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeSitemapPackages(Resource):
    # @ns.expect(xxx_args)
    @ns.marshal_with(sitemap_packages_export_model)
    def get(self, branch):
        url_logging(logger, g.url)
        args = {}
        w = SitemapPackages(g.connection, branch, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/branch_binary_packages/<string:branch>",
    doc={
        "params": {"branch": "branch name"},
        "description": "Get branch binary packages info",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageSetBinaries(Resource):
    @ns.expect(pkgset_packages_args)
    @ns.marshal_with(pkgset_packages_export_model)
    def get(self, branch):
        url_logging(logger, g.url)
        args = pkgset_packages_args.parse_args(strict=True)
        w = PackageSetBinaries(g.connection, branch, **args)
        return run_worker(worker=w, args=args)
