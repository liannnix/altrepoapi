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

import datetime
import json

from flask import request
from uuid import uuid4

from altrepo_api.api.base import APIWorker
from altrepo_api.settings import namespace
from altrepo_api.utils import get_logger

from ..auth import check_auth_ldap
from ..constants import REFRESH_TOKEN_KEY
from ..token.token import STORAGE, encode_jwt_token, user_fingerprint

logger = get_logger(__name__)


class AuthLogin(APIWorker):
    """Authenticates an existing user and return an access and refresh tokens."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.storage = STORAGE
        self.args = kwargs
        self._name = ""
        self._token = ""
        super().__init__()

    def post(self):
        self._name = self.args["nickname"]
        _password = self.args["password"]
        self._token = REFRESH_TOKEN_KEY.format(user=self._name)

        ldap_auth = check_auth_ldap(
            self._name, _password, list(namespace.ACCESS_GROUPS.values())
        )

        if ldap_auth.verified is False:
            return {"message": ldap_auth.error}, 401

        user_groups = ldap_auth.value["groups"]

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
            return {"message": "Unauthorized"}, 401

        encoded_jwt = encode_jwt_token(
            {
                "nickname": self._name,
                "fingerprint": fingerprint,
                "exp": token_expires,
                "groups": user_groups,
            }
        )

        response = {"access_token": encoded_jwt, "refresh_token": refresh_token}
        headers = {
            "Set-Cookie": f"refresh_token={refresh_token}; Expires=f'{cookie_expires}'; HttpOnly"
        }

        return response, 200, headers

    def add_refresh_session(self):
        """
        Adds new session if stored user sessions does not exceeds MAX_REFRESH_SESSIONS_COUNT,
        else remove all user sessions and create a new session.
        """
        fingerprint = user_fingerprint(request)

        if self._exceeds_max_sessions():
            self.storage.delete(self._token)

        token = self._add_refresh_session(fingerprint)

        return token, fingerprint

    def _exceeds_max_sessions(self) -> bool:
        """
        Checks the number of sessions with the same user nickname.
        """
        user_sessions = self.storage.map_getall(self._token)
        return len(user_sessions.keys()) >= namespace.MAX_REFRESH_SESSIONS_COUNT

    def _add_refresh_session(self, fingerprint: str):
        """
        Adds session to the storage, if the session exists, raises an exception.
        """
        user_sessions = self.storage.map_getall(self._token)
        active_fingerprints = {
            json.loads(el).get("fingerprint", None) for el in user_sessions.values()
        }

        if fingerprint not in active_fingerprints:
            return self._new_refresh_token(fingerprint)

        for key, values in user_sessions.items():
            if fingerprint == json.loads(values)["fingerprint"]:
                return key

    def _new_refresh_token(self, fingerprint: str):
        """
        Creates session data and saves it in the storage.
        """
        token = str(uuid4())

        new_refresh_session = {
            token: json.dumps(
                {
                    "nickname": self._name,
                    "fingerprint": fingerprint,
                    "expires": namespace.EXPIRES_REFRESH_TOKEN,
                    "create_at": int(datetime.datetime.now().timestamp()),
                }
            )
        }

        self.storage.map_set(self._token, new_refresh_session)

        return token
