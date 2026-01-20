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

from flask import g
from flask_restx import Resource

from altrepo_api.utils import get_logger, url_logging
from altrepo_api.api.base import run_worker, GET_RESPONSES_404, GET_RESPONSES_400_404

from .namespace import get_namespace
from .endpoints.pkgset_info import (
    AllPackagesets,
    PkgsetCategoriesCount,
    AllPackagesetArchs,
)
from .endpoints.tasks_history import TasksHistory
from .parsers import (
    all_archs_args,
    pkgset_categories_args,
    task_id_args,
)
from .serializers import (
    all_archs_model,
    all_pkgsets_model,
    pkgset_categories_model,
    all_pkgsets_summary_model,
    pkgsets_summary_status_model,
    tasks_history_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/all_pkgsets",
    doc={
        "description": "Get package sets list",
        "responses": GET_RESPONSES_404,
    },
)
class routeAllPackagesets(Resource):
    # @ns.expect()
    @ns.marshal_with(all_pkgsets_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = AllPackagesets(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/all_pkgsets_with_src_count",
    doc={
        "description": ("Get package sets list with source packages count"),
        "responses": GET_RESPONSES_404,
    },
)
class routeAllPackagesetsSourceCount(Resource):
    # @ns.expect()
    @ns.marshal_with(all_pkgsets_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = AllPackagesets(g.connection, **args)
        return run_worker(worker=w, args=args, run_method=w.get_with_pkgs_count)


@ns.route(
    "/all_pkgsets_summary",
    doc={
        "description": "Get package sets list with source packages count",
        "responses": GET_RESPONSES_404,
    },
)
class routeAllPackagesetsSummary(Resource):
    # @ns.expect()
    @ns.marshal_with(all_pkgsets_summary_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = AllPackagesets(g.connection, **args)
        return run_worker(worker=w, args=args, run_method=w.get_summary)


@ns.route(
    "/pkgsets_summary_status",
    doc={
        "description": (
            "Get package sets list with source packages count and status info"
        ),
        "responses": GET_RESPONSES_404,
    },
)
class routePackagesetsSummaryStatus(Resource):
    # @ns.expect()
    @ns.marshal_with(pkgsets_summary_status_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = AllPackagesets(g.connection, **args)
        return run_worker(worker=w, args=args, run_method=w.get_summary_status)


@ns.route(
    "/all_pkgset_archs",
    doc={
        "description": "Get binary package archs list",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeAllPackagesetArchs(Resource):
    @ns.expect(all_archs_args)
    @ns.marshal_with(all_archs_model)
    def get(self):
        url_logging(logger, g.url)
        args = all_archs_args.parse_args(strict=True)
        w = AllPackagesetArchs(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/all_pkgset_archs_with_src_count",
    doc={
        "description": ("Get binary package archs list with source packages count"),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeAllPackagesetArchsSourceCount(Resource):
    @ns.expect(all_archs_args)
    @ns.marshal_with(all_archs_model)
    def get(self):
        url_logging(logger, g.url)
        args = all_archs_args.parse_args(strict=True)
        w = AllPackagesetArchs(g.connection, **args)
        return run_worker(worker=w, args=args, run_method=w.get_with_src_count)


@ns.route(
    "/pkgset_categories_count",
    doc={
        "description": (
            "Get list of package categories with count for given package set"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routePkgsetCategoriesCount(Resource):
    @ns.expect(pkgset_categories_args)
    @ns.marshal_with(pkgset_categories_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgset_categories_args.parse_args(strict=True)
        w = PkgsetCategoriesCount(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/tasks_history",
    doc={
        "description": ("Get history of done tasks for an active branches"),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTasksHistory(Resource):
    @ns.expect(task_id_args)
    @ns.marshal_with(tasks_history_model)
    def get(self):
        url_logging(logger, g.url)
        args = task_id_args.parse_args(strict=True)
        w = TasksHistory(g.connection, **args)
        return run_worker(worker=w, args=args)
