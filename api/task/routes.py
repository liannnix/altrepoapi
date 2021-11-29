# altrepodb API
# Copyright (C) 2021  BaseALT Ltd

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
from flask_restx import Resource, abort, Namespace

from utils import get_logger, url_logging, response_error_parser

from .namespace import get_namespace
from .endpoints.task_diff import TaskDiff, TaskHistory
from .endpoints.task_info import TaskInfo
from .endpoints.task_repo import TaskRepo
from .endpoints.find_packageset import FindPackageset
from .endpoints.misconflict_packages import TaskMisconflictPackages
from .endpoints.build_dependency_set import TaskBuildDependencySet
from .endpoints.task_build_dependency import TaskBuildDependency
from .parsers import (
    task_info_args,
    task_repo_args,
    task_misconflict_args,
    task_build_dep_args,
    task_find_pkgset_args,
    task_buid_dep_set_args,
    task_history_args,
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
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/task_info/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": "Get information for task by ID",
        "responses": {
            200: "Success",
            400: "Request parameters validation error",
            404: "Task ID not found in database",
        },
    },
)
class routeTaskInfo(Resource):
    @ns.expect(task_info_args)
    @ns.marshal_with(task_info_model, as_list=True)
    def get(self, id):
        args = task_info_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = TaskInfo(g.connection, id, **args)
        if not wrk.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/task_repo/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": "Get repository state by ID",
        "responses": {
            400: "Request parameters validation error",
            404: "Task ID not found in database",
        },
    },
)
class routeTaskRepo(Resource):
    @ns.expect(task_repo_args)
    @ns.marshal_with(task_repo_model)
    def get(self, id):
        args = task_repo_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = TaskRepo(g.connection, id, **args)
        if not wrk.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/task_diff/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": "Get task difference by ID",
        "responses": {404: "Task ID not found in database"},
    },
)
class routeTaskDiff(Resource):
    @ns.marshal_with(task_diff_model)
    def get(self, id):
        url_logging(logger, g.url)
        wrk = TaskDiff(g.connection, id)
        if not wrk.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/what_depends_src/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": "Get packages build dependencies",
        "responses": {
            400: "Request parameters validation error",
            404: "Requested data not found in database",
        },
    },
)
class routeTaskBuildDependency(Resource):
    @ns.expect(task_build_dep_args)
    @ns.marshal_with(task_build_dep_model)
    def get(self, id):
        args = task_build_dep_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = TaskBuildDependency(g.connection, id, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        if not wrk.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/misconflict/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": (
            "Get packages with conflicting files in packages "
            "from task that do not have a conflict in dependencies"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Requested data not found in database",
        },
    },
)
class routeTaskMisconflictPackages(Resource):
    @ns.expect(task_misconflict_args)
    @ns.marshal_with(misconflict_pkgs_model)
    def get(self, id):
        args = task_misconflict_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = TaskMisconflictPackages(g.connection, id, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        if not wrk.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/find_packageset/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": (
            "Get information about packages from package sets "
            "by list of source packages from task"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Task ID not found in database",
        },
    },
)
class routeTaskFindPackageset(Resource):
    @ns.expect(task_find_pkgset_args)
    @ns.marshal_with(task_find_pkgset_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = task_find_pkgset_args.parse_args(strict=True)
        wrk = FindPackageset(g.connection, id, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        if not wrk.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/build_dependency_set/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": (
            "Get list of packages required for build by "
            "source packages from task recursively"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Task ID not found in database",
        },
    },
)
class routeTaskBuildDependencySet(Resource):
    @ns.expect(task_buid_dep_set_args)
    @ns.marshal_with(build_dep_set_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = task_buid_dep_set_args.parse_args(strict=True)
        wrk = TaskBuildDependencySet(g.connection, id, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        if not wrk.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/task_history",
    doc={
        "description": "Get done tasks history for branch",
        "responses": {
            400: "Request parameters validation error",
            404: "Requested data not found in database",
        },
    },
)
class routeTaskHistory(Resource):
    @ns.expect(task_history_args)
    @ns.marshal_with(task_history_model)
    def get(self):
        args = task_history_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = TaskHistory(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code
