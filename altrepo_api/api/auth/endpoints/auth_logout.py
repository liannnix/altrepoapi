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
import jwt
import redis
from flask import request

from altrepo_api.api.base import APIWorker
from altrepo_api.settings import namespace
from .blacklisted_token import BlacklistedAccessToken
from ..constants import REFRESH_TOKEN_KEY
from ..exceptions import ApiUnauthorized


class AuthLogout(APIWorker):
    """Authenticate an existing user and return an access token."""

    def __init__(self, connection, payload, **kwargs):
        self.conn = connection
        self.payload = payload
        self.args = kwargs
        self.conn_redis = redis.from_url(namespace.REDIS_URL, db=0)
        self.refresh_token = request.cookies.get("refresh_token")
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.refresh_token is False:
            self.validation_results.append("User is not authorized")

        if self.validation_results != []:
            return False
        else:
            return True

    def post(self):
        access_token = self.args["token"]
        token_payload = jwt.decode(access_token, namespace.ADMIN_PASSWORD, algorithms=["HS256"])
        user_sessions = self.conn_redis.hgetall(
            REFRESH_TOKEN_KEY.format(user=token_payload.get("nickname", ""))
        )
        blacklisted = BlacklistedAccessToken(access_token, self.args["exp"])
        check_access_token = blacklisted.check_blacklist()

        if check_access_token:
            raise ApiUnauthorized(description="Access token is not valid.")
        else:
            blacklisted.write_to_blacklist()

        if self.refresh_token.encode() in user_sessions.keys():
            del user_sessions[self.refresh_token.encode()]
            if not user_sessions:
                self.conn_redis.delete(
                    REFRESH_TOKEN_KEY.format(user=token_payload.get("nickname", ""))
                )
            else:
                self.conn_redis.hdel(
                    REFRESH_TOKEN_KEY.format(user=token_payload.get("nickname", "")),
                    self.refresh_token
                )
        else:
            raise ApiUnauthorized(description="User not authorized")

        return "you successfully logged out", 201
