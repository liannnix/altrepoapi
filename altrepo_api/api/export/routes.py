# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

from flask import g, abort
from flask_restx import Resource

from altrepo_api.utils import (
    get_logger,
    url_logging,
    response_error_parser,
    send_file_compat,
)
from altrepo_api.api.base import run_worker, GET_RESPONSES_404, GET_RESPONSES_400_404

from .namespace import get_namespace
from .endpoints.repology import RepologyExport
from .endpoints.sitemap import SitemapPackages
from .endpoints.packageset import PackageSetBinaries
from .endpoints.translation import TranslationExport
from .endpoints.branch_tree import BranchTreeExport
from .endpoints.beehive import BeehiveFTBFS

from .parsers import pkgset_packages_args, translation_export_args, beehive_args
from .serializers import (
    repology_export_model,
    sitemap_packages_export_model,
    pkgset_packages_export_model,
    branch_tree_model,
    beehive_ftbfs_list_model,
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


@ns.route(
    "/translation/packages_po_files",
    doc={
        "description": (
            "Get an archive of PO files with package's summary "
            "and description for translation purpose"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTranslationExport(Resource):
    @ns.expect(translation_export_args)
    # @ns.marshal_with(translation_export_model)
    @ns.produces(["application/zip"])
    def get(self):
        url_logging(logger, g.url)
        args = translation_export_args.parse_args(strict=True)
        w = TranslationExport(g.connection, **args)
        if not w.check_params():
            abort(
                400,
                message="Request parameters validation error",
                args=args,
                validation_message=w.validation_results,
            )
        result, code = w.get()
        if code != 200:
            abort(code, **response_error_parser(result))
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
    "/branch_tree",
    doc={
        "description": "Branch tree info export",
        "responses": GET_RESPONSES_404,
    },
)
class routeBranchTreeExport(Resource):
    # @ns.expect(xxx_args)
    @ns.marshal_with(branch_tree_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = BranchTreeExport(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/beehive/ftbfs",
    doc={
        "description": "Beehive rebuild errors export",
        "responses": GET_RESPONSES_404,
    },
)
class routeBeehiveFTBFS(Resource):
    @ns.expect(beehive_args)
    @ns.marshal_with(beehive_ftbfs_list_model)
    def get(self):
        url_logging(logger, g.url)
        args = beehive_args.parse_args(strict=True)
        w = BeehiveFTBFS(g.connection, **args)
        return run_worker(worker=w, args=args)
