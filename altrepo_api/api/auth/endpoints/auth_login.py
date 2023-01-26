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

from uuid import uuid4

from flask import request

from altrepo_api.api.base import APIWorker
from altrepo_api.settings import namespace
from altrepo_api.utils import get_fingerprint_to_md5, get_logger
from ..constants import REFRESH_TOKEN_KEY
from ..exceptions import ApiUnauthorized
from ..sql import sql
from ...auth.auth import check_auth_ldap

logger = get_logger(__name__)


class AuthLogin(APIWorker):
    """Authenticate an existing user and return an access token."""

    def __init__(self, connection, payload, **kwargs):
        self.conn = connection
        self.conn_redis = redis.from_url(namespace.REDIS_URL, db=0)
        self.payload = payload
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        ldap_auth = check_auth_ldap(
            self.args["nickname"], self.args["password"], "packages_users"
        )

        if ldap_auth.verified is False:
            self.validation_results.append(ldap_auth.error)

        if self.validation_results != []:
            return False
        else:
            return True

    def post(self):
        cookie_expires = (
            datetime.datetime.now()
            + datetime.timedelta(seconds=namespace.EXPIRES_REFRESH_TOKEN)
        ).ctime()

        token_expires = datetime.datetime.now(
            tz=datetime.timezone.utc
        ) + datetime.timedelta(seconds=namespace.EXPIRES_ACCESS_TOKEN)

        refresh_token, fingerprint = self.add_refresh_session()

        if not refresh_token:
            logger.warning("Refresh token is None")
            return "failed to authorization", 401

        payload = {
            "nickname": self.args["nickname"],
            "fingerprint": fingerprint,
            "exp": token_expires,
        }
        encoded_jwt = jwt.encode(payload, namespace.ADMIN_PASSWORD, algorithm="HS256")

        res = {"access_token": encoded_jwt, "refresh_token": refresh_token}

        http_header = {
            "Set-Cookie": f"refresh_token={refresh_token}; Expires=f'{cookie_expires}'; HttpOnly"
        }
        return res, 201, http_header

    def add_refresh_session(self):
        """
        Add new session If self.valid_session_count return True,
        else remove all user sessions and create a new session.
        """
        fingerprint = get_fingerprint_to_md5(request)
        if self.valid_session_count():
            token = self._add_refresh_session(fingerprint)
        else:
            self.conn_redis.delete(REFRESH_TOKEN_KEY.format(user=self.args["nickname"]))
            token = self._add_refresh_session(fingerprint)
        return token, fingerprint

    def valid_session_count(self) -> bool:
        """
        Check the number of sessions with the same user nickname.
        """
        user_sessions = self.conn_redis.hgetall(
            REFRESH_TOKEN_KEY.format(user=self.args["nickname"])
        )
        return len(user_sessions.keys()) < namespace.MAX_REFRESH_SESSIONS_COUNT

    def _add_refresh_session(self, fingerprint: str):
        """
        Add session to the Redis server, if the session exists, raise an exception
        """
        user_sessions = self.conn_redis.hgetall(
            REFRESH_TOKEN_KEY.format(user=self.args["nickname"])
        )
        active_fingerprints = [
            json.loads(el).get("fingerprint", None) for el in user_sessions.values()
        ]

        if fingerprint not in active_fingerprints:
            return self._new_refresh_token(fingerprint)
        else:
            logger.warning("this user is already logged in")
            raise ApiUnauthorized(description="failed to authorization")

    def _new_refresh_token(self, fingerprint):
        """
        Create session data and send it to the Redis server.
        """
        token = str(uuid4())
        new_refresh_session = {
            token: json.dumps(
                {
                    "nickname": self.args["nickname"],
                    "fingerprint": fingerprint,
                    "expires": namespace.EXPIRES_REFRESH_TOKEN,
                    "create_at": int(datetime.datetime.now().timestamp()),
                }
            )
        }
        self.conn_redis.hmset(
            REFRESH_TOKEN_KEY.format(user=self.args["nickname"]), new_refresh_session
        )
        return token
