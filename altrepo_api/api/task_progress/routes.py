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
from altrepo_api.api.base import run_worker, GET_RESPONSES_400_404, GET_RESPONSES_404
from .endpoints.find_tasks import FindTasks, FindTasksLookup
from .endpoints.packageset import AllTasksBraches
from .endpoints.last_tasks import LastTasks
from .endpoints.task_info import TaskInfo

from .namespace import get_namespace
from .parsers import last_tasks_args, find_tasks_args, find_tasks_lookup_args
from .serializers import (
    tasks_list_model,
    all_tasks_branches_model,
    find_tasks_model,
    task_info_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/last_tasks",
    doc={
        "description": "Get the latest tasks changes",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeLastTasks(Resource):
    @ns.expect(last_tasks_args)
    @ns.marshal_with(tasks_list_model)
    def get(self):
        url_logging(logger, g.url)
        args = last_tasks_args.parse_args(strict=True)
        w = LastTasks(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/all_packagesets",
    doc={
        "deprecated": True,
        "description": "Alias for 'all_tasks_branches' for compatibility",
    },
)
@ns.route("/all_tasks_branches")
@ns.doc(
    description="Get branches list for last tasks",
    responses=GET_RESPONSES_404,
)
class routeAllTasksBraches(Resource):
    # @ns.expect()
    @ns.marshal_with(all_tasks_branches_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = AllTasksBraches(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/find_tasks_lookup",
    doc={
        "description": "Task search by ID, owner, repo, state and component.",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeFindTasksLookup(Resource):
    @ns.expect(find_tasks_lookup_args)
    @ns.marshal_with(find_tasks_model)
    def get(self):
        url_logging(logger, g.url)
        args = find_tasks_lookup_args.parse_args(strict=True)
        w = FindTasksLookup(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/find_tasks",
    doc={
        "description": "Task search by ID, task owner or component.",
        "responses": GET_RESPONSES_404,
    },
)
class routeFindTasks(Resource):
    @ns.expect(find_tasks_args)
    @ns.marshal_with(tasks_list_model)
    def get(self):
        url_logging(logger, g.url)
        args = find_tasks_args.parse_args(strict=True)
        w = FindTasks(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/task_info/<int:id>",
    doc={
        "params": {"id": "task ID"},
        "description": "Get information for task by ID",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTaskInfo(Resource):
    @ns.marshal_with(task_info_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = {}
        w = TaskInfo(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)
