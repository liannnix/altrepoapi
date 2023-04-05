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
from .parsers import oval_export_args
from .serializers import oval_export_model
from .endpoints.oval import OvalExport

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/export/oval/<string:branch>",
    doc={
        "description": "Get OVAL definitions of closed issues of branch packages",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeOvalExport(Resource):
    @ns.expect(oval_export_args)
    @ns.marshal_list_with(oval_export_model)
    def get(self, branch):
        url_logging(logger, g.url)
        args = oval_export_args.parse_args(strict=True)
        w = OvalExport(g.connection, branch, **args)
        return run_worker(worker=w, args=args)
