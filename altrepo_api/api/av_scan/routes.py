# ALTRepo API
# Copyright (C) 2024 BaseALT Ltd

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

from altrepo_api.api.base import run_worker, GET_RESPONSES_400_404, GET_RESPONSES_404
from altrepo_api.utils import get_logger, url_logging
from altrepo_api.settings import namespace as settings
from altrepo_api.api.auth.decorators import token_required

from .endpoints.av_results import AntivirusScanResults
from .endpoints.av_issues import AntivirusScanIssueList, AntivirusScanBranchesList
from .namespace import get_namespace
from .parsers import av_results_args, av_issues_args
from .serializers import (
    avs_issue_list_response_model,
    avs_list_response_model,
    av_branches_response_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/detections",
    doc={
        "description": "Get Antivirus detections list",
        "responses": GET_RESPONSES_400_404,
        "security": "Bearer",
    },
)
class routeAntivirusScanList(Resource):
    @ns.expect(av_results_args)
    @ns.marshal_with(avs_list_response_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = av_results_args.parse_args(strict=True)
        w = AntivirusScanResults(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/issues",
    doc={
        "description": "Get Antivirus detections list for issues",
        "responses": GET_RESPONSES_404,
        "security": "Bearer",
    },
)
class routeAntivirusScanIssuesList(Resource):
    @ns.expect(av_issues_args)
    @ns.marshal_with(avs_issue_list_response_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = av_issues_args.parse_args(strict=True)
        w = AntivirusScanIssueList(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/branches",
    doc={
        "description": "Get Antivirus scanned branches list",
        "responses": GET_RESPONSES_404,
        "security": "Bearer",
    },
)
class routeAntivirusScanBranchesList(Resource):
    # @ns.expect()
    @ns.marshal_with(av_branches_response_model)
    @token_required(settings.KEYCLOAK_MANAGE_LIST_ROLE)
    def get(self):
        url_logging(logger, g.url)
        args = av_issues_args.parse_args(strict=True)
        w = AntivirusScanBranchesList(g.connection, **args)
        return run_worker(worker=w, args=args)
