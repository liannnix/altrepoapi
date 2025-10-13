# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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
from altrepo_api.api.base import run_worker, POST_RESPONSES_401, POST_RESPONSES_401_403
from .decorators import token_required
from .endpoints.auth_login import AuthLogin
from .endpoints.auth_logout import AuthLogout
from .endpoints.refresh_token import RefreshToken

from .namespace import get_namespace
from .parsers import login_args, refresh_token_args

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/login",
    doc={
        "description": "Authenticate an existing user and return an access token.",
        "responses": POST_RESPONSES_401,
    },
)
class routeAuthLogin(Resource):
    @ns.expect(login_args)
    # @ns.marshal_with(xxx)
    def post(self):
        url_logging(logger, g.url)
        args = login_args.parse_args(strict=True)
        w = AuthLogin(g.connection, **args)
        return run_worker(
            worker=w,
            args=args,
            run_method=w.post,
            check_method=w.check_params_post,
        )


@ns.route(
    "/logout",
    doc={
        "description": "User logs out.",
        "responses": POST_RESPONSES_401_403,
    },
)
class routeAuthLogout(Resource):
    @ns.doc(security="Bearer")
    @token_required("", validate_role=False)
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = AuthLogout(g.connection, self.post.token, self.post.exp, **args)  # type: ignore
        return run_worker(worker=w, args=args, run_method=w.post)


@ns.route(
    "/refresh-token",
    doc={
        "description": "Update access token.",
        "responses": POST_RESPONSES_401,
    },
)
class routeRefreshToken(Resource):
    @ns.expect(refresh_token_args)
    def post(self):
        url_logging(logger, g.url)
        args = refresh_token_args.parse_args(strict=True)
        w = RefreshToken(g.connection, **args)
        return run_worker(worker=w, args=args, run_method=w.post)
