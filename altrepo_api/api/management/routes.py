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

from altrepo_api.api.base import (
    run_worker,
    GET_RESPONSES_400_404,
    POST_RESPONSES_400_404,
)
from altrepo_api.utils import get_logger, url_logging

from .namespace import get_namespace
from .endpoints.manage import ManageErrata
from .endpoints.task_info import TaskInfo
from .endpoints.task_list import TaskList
from .endpoints.vulns_info import VulnsInfo
from .parsers import task_list_args
from .serializers import (
    task_list_model,
    task_info_model,
    vuln_ids_json_list_model,
    vuln_ids_json_post_list_model,
    errata_manage_model,
    errata_manage_response_model,
)


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


@ns.route(
    "/task_info/<int:id>",
    doc={
        "description": "Get information about the task in the state "
        "'DONE' and a list of vulnerabilities for subtasks "
        "based on task ID.",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeTaskInfo(Resource):
    # @ns.expect()
    @ns.marshal_with(task_info_model)
    def get(self, id):
        url_logging(logger, g.url)
        args = {}
        w = TaskInfo(g.connection, id, **args)
        if not w.check_task_id():
            ns.abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        return run_worker(worker=w, args=args)


@ns.route(
    "/vulns",
    doc={
        "description": "Find vulnerability information.",
        "responses": POST_RESPONSES_400_404,
    },
)
class routeVulnsInfo(Resource):
    @ns.expect(vuln_ids_json_post_list_model)
    @ns.marshal_with(vuln_ids_json_list_model)
    def post(self):
        url_logging(logger, g.url)
        w = VulnsInfo(g.connection, json_data=ns.payload)
        return run_worker(
            worker=w, run_method=w.post, check_method=w.check_params_post, ok_code=200
        )


RESPONSES_400_409 = {
    200: "Data loaded",
    400: "Request payload validation error",
    409: "Requests payload inconsistent with DB contents",
}
RESPONSES_400_404_409 = {
    200: "Data loaded",
    400: "Request payload validation error",
    404: "Requested data not found in database",
    409: "Requests payload inconsistent with DB contents",
}


@ns.route("/errata")
class routeManageErrata(Resource):
    @ns.doc(
        description="Get errata info.",
        responses=GET_RESPONSES_400_404,
    )
    # @ns.expect(errata_manage_get_args)
    @ns.marshal_with(errata_manage_response_model)
    def get(self):
        url_logging(logger, g.url)
        # args = errata_manage_get_args.parse_args(strict=True)
        args = {}
        w = ManageErrata(g.connection, payload={}, **args)
        return run_worker(worker=w, args=args)

    @ns.doc(
        description="Update errata version with new contents.",
        responses=RESPONSES_400_404_409,
    )
    @ns.expect(errata_manage_model)
    @ns.marshal_with(errata_manage_response_model)
    def put(self):
        url_logging(logger, g.url)
        w = ManageErrata(g.connection, payload=ns.payload)
        return run_worker(
            worker=w, run_method=w.put, check_method=w.check_params_put, ok_code=200
        )

    @ns.doc(
        description="Register new errata record.",
        responses=RESPONSES_400_409,
    )
    @ns.expect(errata_manage_model)
    @ns.marshal_with(errata_manage_response_model)
    def post(self):
        url_logging(logger, g.url)
        w = ManageErrata(g.connection, payload=ns.payload)
        return run_worker(
            worker=w, run_method=w.post, check_method=w.check_params_post, ok_code=200
        )

    @ns.doc(description="Discard errata record.", responses=GET_RESPONSES_400_404)
    @ns.expect(errata_manage_model)
    @ns.marshal_with(errata_manage_response_model)
    def delete(self):
        url_logging(logger, g.url)
        w = ManageErrata(g.connection, payload=ns.payload)
        return run_worker(
            worker=w,
            run_method=w.delete,
            check_method=w.check_params_delete,
            ok_code=200,
        )
