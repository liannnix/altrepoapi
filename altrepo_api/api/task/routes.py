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
from altrepo_api.api.base import run_worker, GET_RESPONSES_404, GET_RESPONSES_400_404

from .namespace import get_namespace
from .endpoints.task_diff import TaskDiff, TaskHistory
from .endpoints.task_info import TaskInfo
from .endpoints.task_repo import TaskRepo
from .endpoints.find_packageset import FindPackageset
from .endpoints.misconflict_packages import TaskMisconflictPackages
from .endpoints.build_dependency_set import TaskBuildDependencySet
from .endpoints.task_build_dependency import TaskBuildDependency
from .endpoints.find_images import FindImages
from .endpoints.task_packages import TaskPackages
from .endpoints.needs_approval import NeedsApproval
from .parsers import (
    task_info_args,
    task_repo_args,
    task_misconflict_args,
    task_build_dep_args,
    task_find_pkgset_args,
    task_buid_dep_set_args,
    task_history_args,
    needs_approval_args,
)
from .serializers import (
    task_info_model,
    task_repo_model,
    task_diff_model,
    build_dep_set_model,
    task_build_dep_model,
    misconflict_pkgs_model,
    task_find_pkgset_model,
    task_history_model,
    find_images_by_task_model,
    task_packages_model,
    needs_approval_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/task_info/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": "Get information for task by ID",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTaskInfo(Resource):
    @ns.expect(task_info_args)
    @ns.marshal_with(task_info_model, as_list=True)
    def get(self, id):
        url_logging(logger, g.url)
        args = task_info_args.parse_args(strict=True)
        w = TaskInfo(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)


@ns.route(
    "/task_repo/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": "Get repository state by ID",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTaskRepo(Resource):
    @ns.expect(task_repo_args)
    @ns.marshal_with(task_repo_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = task_repo_args.parse_args(strict=True)
        w = TaskRepo(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)


@ns.route(
    "/task_diff/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": "Get task difference by ID",
        "responses": GET_RESPONSES_404,
    },
)
class routeTaskDiff(Resource):
    @ns.marshal_with(task_diff_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = {}
        w = TaskDiff(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)


@ns.route(
    "/what_depends_src/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": "Get packages build dependencies",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTaskBuildDependency(Resource):
    @ns.expect(task_build_dep_args)
    @ns.marshal_with(task_build_dep_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = task_build_dep_args.parse_args(strict=True)
        w = TaskBuildDependency(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)


@ns.route(
    "/misconflict/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": (
            "Get packages with conflicting files in packages "
            "from task that do not have a conflict in dependencies"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTaskMisconflictPackages(Resource):
    @ns.expect(task_misconflict_args)
    @ns.marshal_with(misconflict_pkgs_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = task_misconflict_args.parse_args(strict=True)
        w = TaskMisconflictPackages(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)


@ns.route(
    "/find_packageset/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": (
            "Get information about packages from package sets "
            "by list of source packages from task"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTaskFindPackageset(Resource):
    @ns.expect(task_find_pkgset_args)
    @ns.marshal_with(task_find_pkgset_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = task_find_pkgset_args.parse_args(strict=True)
        w = FindPackageset(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)


@ns.route(
    "/build_dependency_set/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": (
            "Get list of packages required for build by "
            "source packages from task recursively"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTaskBuildDependencySet(Resource):
    @ns.expect(task_buid_dep_set_args)
    @ns.marshal_with(build_dep_set_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = task_buid_dep_set_args.parse_args(strict=True)
        w = TaskBuildDependencySet(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)


@ns.route(
    "/task_history",
    doc={
        "description": "Get done tasks history for branch",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTaskHistory(Resource):
    @ns.expect(task_history_args)
    @ns.marshal_with(task_history_model)
    def get(self):
        url_logging(logger, g.url)
        args = task_history_args.parse_args(strict=True)
        w = TaskHistory(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/find_images/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": (
            "Get the newest images which contain binary packages with the same "
            "names as binaries from a task with one of the following states: "
            "EPERM, TESTED or DONE. "
            "Listed only active images for task's branch."
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeFindImages(Resource):
    # @ns.expect()
    @ns.marshal_with(find_images_by_task_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = {}
        w = FindImages(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)


@ns.route(
    "/packages/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": ("Get information about packages from task "),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTaskPackages(Resource):
    # @ns.expect()
    @ns.marshal_with(task_packages_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = {}
        w = TaskPackages(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)


@ns.route(
    "/needs_approval",
    doc={
        "description": "Get EPERM tasks which require approval",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeNeedsApproval(Resource):
    @ns.expect(needs_approval_args)
    @ns.marshal_with(needs_approval_model)
    def get(self):
        url_logging(logger, g.url)
        args = needs_approval_args.parse_args(strict=True)
        w = NeedsApproval(g.connection, **args)
        return run_worker(worker=w, args=args)
