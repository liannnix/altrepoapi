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
import datetime
import json

import jwt
import redis
from flask import request

from altrepo_api.api.auth.constants import REFRESH_TOKEN_KEY
from altrepo_api.api.auth.endpoints.blacklisted_token import BlacklistedAccessToken
from altrepo_api.api.auth.exceptions import ApiUnauthorized
from altrepo_api.api.base import APIWorker
from altrepo_api.settings import namespace
from altrepo_api.utils import get_fingerprint_to_md5


class RefreshToken(APIWorker):
    """Authenticate an existing user and return an access token."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.conn_redis = redis.from_url(namespace.REDIS_URL, db=0)
        self.refresh_token = request.cookies.get("refresh_token")
        self.access_token = self.args["access_token"]
        self.access_token_payload = jwt.decode(
            self.access_token,
            namespace.ADMIN_PASSWORD,
            algorithms=["HS256"],
            options={"verify_signature": False},
        )
        self.blacklisted = BlacklistedAccessToken(
            self.access_token, self.access_token_payload["exp"]
        )
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.blacklisted.get_token_from_blacklist():
            self.validation_results.append("Token to blacklisted")

        if self.refresh_token is None:
            self.validation_results.append("User is not authorized")

        if self.validation_results != []:
            return False
        else:
            return True

    def post(self):
        user_sessions = self.conn_redis.hgetall(
            REFRESH_TOKEN_KEY.format(user=self.access_token_payload.get("nickname", ""))
        )
        active_session = user_sessions.get(self.refresh_token.encode())
        if not active_session:
            raise ApiUnauthorized(description="User not authorized.")

        session_data_to_dict = json.loads(active_session)
        if self.check_fingerprint(session_data_to_dict.get("fingerprint")):
            raise ApiUnauthorized(description="User not authorized.")

        if (
            session_data_to_dict["create_at"] + session_data_to_dict["expires"]
            <= datetime.datetime.now().timestamp()
        ):
            self.conn_redis.hdel(
                REFRESH_TOKEN_KEY.format(
                    user=self.access_token_payload.get("nickname", "")
                ),
                self.refresh_token,
            )
            raise ApiUnauthorized(description="Session expired")

        self.blacklisted.write_to_blacklist()
        new_access_token = self.new_access_token(self.access_token_payload)

        res = {"access_token": new_access_token, "refresh_token": self.refresh_token}

        return res, 201

    @staticmethod
    def new_access_token(payload):
        token_expires = datetime.datetime.now(
            tz=datetime.timezone.utc
        ) + datetime.timedelta(seconds=namespace.EXPIRES_ACCESS_TOKEN)
        payload["exp"] = token_expires
        encoded_jwt = jwt.encode(payload, namespace.ADMIN_PASSWORD, algorithm="HS256")
        return encoded_jwt

    @staticmethod
    def check_fingerprint(session_fingerprint):
        current_fingerprint = get_fingerprint_to_md5(request)
        return session_fingerprint != current_fingerprint
