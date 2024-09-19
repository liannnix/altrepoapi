# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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
from .endpoints.maintainer import AllMaintainers
from .endpoints.maintainer import MaintainerInfo
from .endpoints.package import MaintainerPackages
from .endpoints.packageset import MaintainerBranches
from .endpoints.repocop import RepocopByMaintainer
from .endpoints.beehive import MaintainerBeehiveErrors
from .endpoints.watch import WatchByMaintainer
from .parsers import (
    all_maintainers_args,
    maintainer_info_args,
    maintainer_branches_args,
    maintainer_packages_args,
    maintainer_watch_args,
)
from .serializers import (
    all_maintainers_model,
    maintainer_info_model,
    maintainer_pkgs_model,
    maintainer_branches_model,
    repocop_by_maintainer_model,
    beehive_by_maintainer_model,
    watch_by_maintainer_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/all_maintainers", doc={"description": "alias for /all_maintainers_with_nicknames"}
)
@ns.route("/all_maintainers_with_nicknames")
@ns.doc(
    description="List of maintainers in branch with nicknames and source packages count",
    responses=GET_RESPONSES_400_404,
)
class routeMaintainersAll(Resource):
    @ns.expect(all_maintainers_args)
    @ns.marshal_list_with(all_maintainers_model)
    def get(self):
        url_logging(logger, g.url)
        args = all_maintainers_args.parse_args(strict=True)
        w = AllMaintainers(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/maintainer_info",
    doc={
        "description": "Maintainer information",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeMaintainersInfo(Resource):
    @ns.expect(maintainer_info_args)
    @ns.marshal_list_with(maintainer_info_model)
    def get(self):
        url_logging(logger, g.url)
        args = maintainer_info_args.parse_args(strict=True)
        w = MaintainerInfo(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/maintainer_packages",
    doc={
        "description": "Packages collected by the specified maintainer",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeMaintainerPackages(Resource):
    @ns.expect(maintainer_packages_args)
    @ns.marshal_list_with(maintainer_pkgs_model)
    def get(self):
        url_logging(logger, g.url)
        args = maintainer_packages_args.parse_args(strict=True)
        w = MaintainerPackages(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/maintainer_branches",
    doc={
        "description": "Packages collected by the specified maintainer",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeMaintainerBranches(Resource):
    @ns.expect(maintainer_branches_args)
    @ns.marshal_list_with(maintainer_branches_model)
    def get(self):
        url_logging(logger, g.url)
        args = maintainer_branches_args.parse_args(strict=True)
        w = MaintainerBranches(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/repocop_by_maintainer",
    doc={
        "description": "Get repocop results by the maintainers nickname",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeRepocopByMaintainer(Resource):
    @ns.expect(maintainer_packages_args)
    @ns.marshal_list_with(repocop_by_maintainer_model)
    def get(self):
        url_logging(logger, g.url)
        args = maintainer_packages_args.parse_args(strict=True)
        w = RepocopByMaintainer(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/beehive_errors_by_maintainer",
    doc={
        "description": "Get Beehive rebuild errors by the maintainer's nickname",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeBeehiveByMaintainer(Resource):
    @ns.expect(maintainer_packages_args)
    @ns.marshal_list_with(beehive_by_maintainer_model)
    def get(self):
        url_logging(logger, g.url)
        args = maintainer_packages_args.parse_args(strict=True)
        w = MaintainerBeehiveErrors(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/watch_by_maintainer",
    doc={
        "description": "Get watch packages by the maintainer's nickname",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeWatchByMaintainer(Resource):
    @ns.expect(maintainer_watch_args)
    @ns.marshal_list_with(watch_by_maintainer_model)
    def get(self):
        url_logging(logger, g.url)
        args = maintainer_watch_args.parse_args(strict=True)
        w = WatchByMaintainer(g.connection, **args)
        return run_worker(worker=w, args=args)
