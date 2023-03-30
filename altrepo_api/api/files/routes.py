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
from .endpoints.file_search import FileSearch, FastFileSearchLookup
from .endpoints.packages_by_file import PackagesByFile

from .namespace import get_namespace
from .parsers import (
    file_search_args,
    fast_file_search_args,
    packages_by_file_args
)
from .serializers import (
    files_model,
    fast_file_search_model,
    packages_by_model
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/file_search",
    doc={
        "description": "Find files by name including partial occurrence.",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeFileSearch(Resource):
    @ns.expect(file_search_args)
    @ns.marshal_with(files_model)
    def get(self):
        url_logging(logger, g.url)
        args = file_search_args.parse_args(strict=True)
        w = FileSearch(g.connection, **args)
        return run_worker(worker=w, run_method=w.get, args=args)


@ns.route(
    "/fast_file_search_lookup",
    doc={
        "description": "Fast search files by name including partial occurrence.",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeFastFileSearchLookup(Resource):
    @ns.expect(fast_file_search_args)
    @ns.marshal_with(fast_file_search_model)
    def get(self):
        url_logging(logger, g.url)
        args = file_search_args.parse_args(strict=True)
        w = FastFileSearchLookup(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/packages_by_file",
    doc={
        "description": "Get a list of packages to which the specified file belongs to.",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackagesByFile(Resource):
    @ns.expect(packages_by_file_args)
    @ns.marshal_with(packages_by_model)
    def get(self):
        url_logging(logger, g.url)
        args = packages_by_file_args.parse_args(strict=True)
        w = PackagesByFile(g.connection, **args)
        return run_worker(worker=w, args=args)
