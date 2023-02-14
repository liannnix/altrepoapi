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
from .parsers import (
    package_bugzilla_args,
    maintainer_bugzilla_args,
    bugzilla_by_edition_args,
)
from .serializers import bugzilla_info_model
from .endpoints.bugzilla_info import Bugzilla

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/bugzilla_by_package",
    doc={
        "description": "Get information from bugzilla by the source package name",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeBugzillaByPackage(Resource):
    @ns.expect(package_bugzilla_args)
    @ns.marshal_list_with(bugzilla_info_model)
    def get(self):
        url_logging(logger, g.url)
        args = package_bugzilla_args.parse_args(strict=True)
        w = Bugzilla(g.connection, **args)
        return run_worker(worker=w, run_method=w.get_bug_by_package, args=args)


@ns.route(
    "/bugzilla_by_image_edition",
    doc={
        "description": "Get information from bugzilla by image edition",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeBugzillaByImageEdition(Resource):
    @ns.expect(bugzilla_by_edition_args)
    @ns.marshal_list_with(bugzilla_info_model)
    def get(self):
        url_logging(logger, g.url)
        args = bugzilla_by_edition_args.parse_args(strict=True)
        w = Bugzilla(g.connection, **args)
        return run_worker(worker=w, run_method=w.get_bugs_by_image_edition, args=args)


@ns.route(
    "/bugzilla_by_maintainer",
    doc={
        "description": "Get information from bugzilla by the maintainer nickname",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeBugzillaByMaintainer(Resource):
    @ns.expect(maintainer_bugzilla_args)
    @ns.marshal_list_with(bugzilla_info_model)
    def get(self):
        url_logging(logger, g.url)
        args = maintainer_bugzilla_args.parse_args(strict=True)
        w = Bugzilla(g.connection, **args)
        return run_worker(worker=w, run_method=w.get_bug_by_maintainer, args=args)
