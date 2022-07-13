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
from altrepo_api.api.base import run_worker, GET_RESPONSES_400_404

from .namespace import get_namespace
from .endpoints.license import LicenseTokens, LicenseInfo
from .parsers import (
    license_info_args,
    license_tokens_args,
)
from .serializers import (
    license_info_model,
    license_tokens_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/tokens",
    doc={
        "description": "Get valid license tokens and SPDX license IDs",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeLicenseTokens(Resource):
    @ns.expect(license_tokens_args)
    @ns.marshal_with(license_tokens_model)
    def get(self):
        url_logging(logger, g.url)
        args = license_tokens_args.parse_args(strict=True)
        w = LicenseTokens(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/info",
    doc={
        "description": "Get license info by SPDX license ID",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeLicenseInfo(Resource):
    @ns.expect(license_info_args)
    @ns.marshal_with(license_info_model)
    def get(self):
        url_logging(logger, g.url)
        args = license_tokens_args.parse_args(strict=True)
        w = LicenseInfo(g.connection, **args)
        return run_worker(worker=w, args=args)
