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

from altrepo_api.api.base import run_worker, GET_RESPONSES_400_404
from altrepo_api.api.management.serializers import task_list_model
from altrepo_api.utils import (
    get_logger,
    url_logging,
)

from altrepo_api.api.management import get_namespace
from altrepo_api.api.management.parsers import task_list_args
from altrepo_api.api.management.endpoints.task_list import TaskList


ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/task_list",
    doc={
        "description": "Get a list of tasks in DONE status."
        "You can also search for issues by ID, task owner, "
        "component or Vulnerability.",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTaskList(Resource):
    @ns.expect(task_list_args)
    @ns.marshal_with(task_list_model)
    def get(self):
        url_logging(logger, g.url)
        args = task_list_args.parse_args(strict=True)
        w = TaskList(g.connection, **args)
        return run_worker(worker=w, args=args)
