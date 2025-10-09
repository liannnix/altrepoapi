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

import datetime
import json

from flask import request

from altrepo_api.api.base import APIWorker

from ..constants import REFRESH_TOKEN_KEY, AuthProvider
from ..exceptions import ApiUnauthorized
from ..keycloak import keycloak_openid
from ..token import (
    STORAGE,
    AccessTokenBlacklist,
    InvalidTokenError,
    check_fingerprint,
    decode_jwt_token,
    update_access_token,
)


class RefreshToken(APIWorker):
    """Authenticate an existing user and return an access token."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.storage = STORAGE
        self.refresh_token = request.cookies.get("refresh_token", "")
        self.access_token = self.args["access_token"]
        self.access_token_payload = {}
        self.access_token_auth_provider: AuthProvider
        self.blacklist: AccessTokenBlacklist
        super().__init__()

    def check_params(self):
        self.logger.debug("args : %s", self.args)
        self.logger.debug("cookies: %s", request.cookies)
        self.validation_results = []

        # check access token and decode it.
        try:
            self.access_token_auth_provider, self.access_token_payload = (
                decode_jwt_token(self.access_token, verify_exp=False)
            )
        except InvalidTokenError:
            self.validation_results.append("Invalid access token")
            return False

        self.blacklist = AccessTokenBlacklist(
            self.access_token, self.access_token_payload["exp"]
        )

        if self.blacklist.get():
            self.validation_results.append("Token is blacklisted")

        if not self.refresh_token:
            self.validation_results.append("User is not authorized")

        return self.validation_results == []

    def post(self):
        if self.access_token_auth_provider == AuthProvider.LDAP:
            user = self.access_token_payload.get("nickname", "")
        else:
            user = self.access_token_payload.get("preferred_username", "")

        user_sessions = self.storage.map_getall(REFRESH_TOKEN_KEY.format(user=user))
        active_session = user_sessions.get(self.refresh_token)

        if not active_session:
            raise ApiUnauthorized(description="User not authorized")

        session_data_json: dict = json.loads(active_session)

        if self.access_token_auth_provider == AuthProvider.LDAP:
            if not check_fingerprint(session_data_json.get("fingerprint", "")):
                raise ApiUnauthorized(description="User not authorized")

        if (
            session_data_json["create_at"] + session_data_json["expires"]
            <= datetime.datetime.now().timestamp()
        ):
            self.storage.map_delete(
                REFRESH_TOKEN_KEY.format(user=user),
                self.refresh_token,
            )
            raise ApiUnauthorized(description="Session is expired")

        # add the old access token to the blacklist if it hasn't expired yet.
        self.blacklist.add()

        if self.access_token_auth_provider == AuthProvider.LDAP:
            new_access_token = update_access_token(self.access_token_payload)
        else:
            jwt = keycloak_openid.refresh_token(self.refresh_token)
            new_access_token = jwt["access_token"]

        return {
            "access_token": new_access_token,
            "refresh_token": self.refresh_token,
        }, 200
