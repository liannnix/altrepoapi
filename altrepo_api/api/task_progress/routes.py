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
from .endpoints.find_tasks import FastTasksSearchLookup, FindTasks
from .endpoints.packageset import AllPackageSets
from .endpoints.last_tasks import LastTasks

from .namespace import get_namespace
from .parsers import last_tasks_args, fast_find_tasks_args, find_tasks_args
from .serializers import tasks_list_model, all_pkgsets_model, fast_tasks_search_model

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
        "description": "Get package sets list for last tasks",
        "responses": GET_RESPONSES_404,
    },
)
class routeAllPackageSets(Resource):
    # @ns.expect()
    @ns.marshal_with(all_pkgsets_model)
    def get(self):
        url_logging(logger, g.url)
        args = {}
        w = AllPackageSets(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/fast_tasks_search_lookup",
    doc={
        "description": "Fast task search by ID, task owner or component.",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeFastTasksSearchLookup(Resource):
    @ns.expect(fast_find_tasks_args)
    @ns.marshal_with(fast_tasks_search_model)
    def get(self):
        url_logging(logger, g.url)
        args = fast_find_tasks_args.parse_args(strict=True)
        w = FastTasksSearchLookup(g.connection, **args)
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
