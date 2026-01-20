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
from altrepo_api.api.auth.decorators import auth_required
from altrepo_api.api.base import (
    run_worker,
    GET_RESPONSES_404,
    GET_RESPONSES_400_404,
    POST_RESPONSES_400_404,
)
from .endpoints.packageset_components import PackagesByUuid
from .endpoints.pkgset_compare import PackagesetCompare
from .endpoints.pkgset_packages import PackagesetPackages
from .endpoints.pkgset_status import RepositoryStatus, ActivePackagesets
from .endpoints.repository_status import RepositoryStatistics
from .endpoints.maintainer_score import MaintainerScoresBatch

from .namespace import get_namespace
from .parsers import (
    pkgset_compare_args,
    pkgset_packages_args,
    repository_statistics_args,
    packages_by_uuid_args,
    packages_by_component_args,
    maintainer_scores_batch_args,
)
from .serializers import (
    pkgset_compare_model,
    pkgset_packages_model,
    pkgset_status_post_model,
    pkgset_status_get_model,
    active_pkgsets_model,
    repository_statistics_model,
    packages_by_uuid_model,
    maintainer_scores_batch_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/repository_packages",
    doc={
        "description": (
            "Get list of packageset packages. "
            "Architecture argument is actual only if type is 'binary'."
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackagesetPackages(Resource):
    @ns.expect(pkgset_packages_args)
    @ns.marshal_with(pkgset_packages_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgset_packages_args.parse_args(strict=True)
        w = PackagesetPackages(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/compare_packagesets",
    doc={
        "description": "Get difference list of packages from two package sets",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackagesetCompare(Resource):
    @ns.expect(pkgset_compare_args)
    @ns.marshal_with(pkgset_compare_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgset_compare_args.parse_args(strict=True)
        w = PackagesetCompare(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route("/pkgset_status")
class routeRepositoryStatus(Resource):
    @ns.doc(
        description="Load package set status into database",
        responses=POST_RESPONSES_400_404,
    )
    @ns.expect(pkgset_status_post_model)
    @ns.doc(security="BasicAuth")
    @auth_required(admin_only=True)
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = RepositoryStatus(g.connection, json_data=ns.payload)
        return run_worker(
            worker=w,
            run_method=w.post,
            check_method=w.check_params_post,
            args=args,
            ok_code=201,
        )

    @ns.doc(
        description="Get package set status into database",
        responses=GET_RESPONSES_400_404,
    )
    @ns.marshal_with(pkgset_status_get_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = RepositoryStatus(g.connection)
        return run_worker(worker=w, args=args)


@ns.route(
    "/active_packagesets",
    doc={
        "description": ("Get list of active package sets"),
        "responses": GET_RESPONSES_404,
    },
)
class routeActivePackagesets(Resource):
    # @ns.expect()
    @ns.marshal_with(active_pkgsets_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = ActivePackagesets(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/repository_statistics",
    doc={
        "description": "Get repository statistics",
        "responses": GET_RESPONSES_404,
    },
)
class routeRepositoryStatistics(Resource):
    @ns.expect(repository_statistics_args)
    @ns.marshal_with(repository_statistics_model)
    def get(self):
        url_logging(logger, g.url)
        args = repository_statistics_args.parse_args(strict=True)
        w = RepositoryStatistics(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/packages_by_uuid",
    doc={
        "description": "Get packages by packageset component UUID",
        "responses": GET_RESPONSES_404,
    },
)
class routePackagesByUuid(Resource):
    @ns.expect(packages_by_uuid_args)
    @ns.marshal_with(packages_by_uuid_model)
    def get(self):
        url_logging(logger, g.url)
        args = packages_by_uuid_args.parse_args(strict=True)
        w = PackagesByUuid(g.connection, **args)
        return run_worker(worker=w, args=args, run_method=w.get_by_uuid)


@ns.route(
    "/packages_by_component",
    doc={
        "description": "Get packages by packageset component and architecture.",
        "responses": GET_RESPONSES_404,
    },
)
class routePackagesByComponent(Resource):
    @ns.expect(packages_by_component_args)
    @ns.marshal_with(packages_by_uuid_model)
    def get(self):
        url_logging(logger, g.url)
        args = packages_by_component_args.parse_args(strict=True)
        w = PackagesByUuid(g.connection, **args)
        return run_worker(worker=w, args=args, run_method=w.get_by_component)


@ns.route(
    "/maintainer_scores",
    doc={
        "description": "Get maintainer scores for all source packages in a branch.",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeMaintainerScoresBatch(Resource):
    @ns.expect(maintainer_scores_batch_args)
    @ns.marshal_with(maintainer_scores_batch_model)
    def get(self):
        url_logging(logger, g.url)
        args = maintainer_scores_batch_args.parse_args(strict=True)
        w = MaintainerScoresBatch(g.connection, **args)
        return run_worker(worker=w, args=args)
