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
from altrepo_api.api.base import run_worker, GET_RESPONSES_400_404

from .namespace import get_namespace
from .endpoints.last_packages import LastTaskPackages
from .endpoints.versions import PackageVersionsFromTasks
from .endpoints.task_info import TasksByPackage, TasksByMaintainer
from .parsers import (
    last_pkgs_args,
    task_by_name_args,
    maintainer_info_args,
    pkgs_versions_from_tasks_args,
)
from .serializers import (
    task_by_name_model,
    last_packages_model,
    pkgs_versions_from_tasks_model,
)


ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/tasks_by_package",
    doc={
        "description": "Get tasks list by source package name",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTasksByPackage(Resource):
    @ns.expect(task_by_name_args)
    @ns.marshal_with(task_by_name_model)
    def get(self):
        url_logging(logger, g.url)
        args = task_by_name_args.parse_args(strict=True)
        w = TasksByPackage(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/last_packages",
    "/last_packages_by_tasks",
    doc={
        "description": ("Get list of last packages from tasks for given parameters"),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeLastTaskPackages(Resource):
    @ns.expect(last_pkgs_args)
    @ns.marshal_with(last_packages_model)
    def get(self):
        url_logging(logger, g.url)
        args = last_pkgs_args.parse_args(strict=True)
        w = LastTaskPackages(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/tasks_by_maintainer",
    doc={
        "description": "Get tasks list by maintainer nickname",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTasksByMaintainer(Resource):
    @ns.expect(maintainer_info_args)
    @ns.marshal_list_with(task_by_name_model)
    def get(self):
        url_logging(logger, g.url)
        args = maintainer_info_args.parse_args(strict=True)
        w = TasksByMaintainer(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/package_versions_from_tasks",
    doc={
        "description": "Get source package versions from tasks",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageVersionsFromTasks(Resource):
    @ns.expect(pkgs_versions_from_tasks_args)
    @ns.marshal_with(pkgs_versions_from_tasks_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgs_versions_from_tasks_args.parse_args(strict=True)
        w = PackageVersionsFromTasks(g.connection, **args)
        return run_worker(worker=w, args=args)
