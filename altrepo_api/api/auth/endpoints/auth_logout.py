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

from flask import request

from altrepo_api.api.base import APIWorker
from ..constants import REFRESH_TOKEN_KEY, AuthProvider
from ..keycloak import keycloak_openid
from ..exceptions import ApiUnauthorized
from ..token import AccessTokenBlacklist, InvalidTokenError, STORAGE, decode_jwt_token


class AuthLogout(APIWorker):
    """
    Implementing user logout using access and refresh tokens.
    If the access token is valid, it is added to the blacklist.
    The refresh token for user logout is taken from cookie files.
    """

    def __init__(self, connection, token: str, token_exp: int, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.token = token
        self.token_exp = token_exp
        self.storage = STORAGE
        self.refresh_token = request.cookies.get("refresh_token", "")
        self.blacklist = AccessTokenBlacklist(self.token, self.token_exp)
        super().__init__()

    def check_params(self):
        self.logger.debug("args : %s", self.args)
        self.validation_results = []

        if self.refresh_token is None:
            self.validation_results.append("User is not authorized")

        return self.validation_results == []

    def post(self):
        try:
            # JWT token already validated in `@token_required` decorator
            auth_provider, token_payload = decode_jwt_token(self.token)
        except InvalidTokenError:
            raise ApiUnauthorized(description="Invalid token")

        if auth_provider == AuthProvider.LDAP:
            user = token_payload.get("nickname", "")
        else:
            user = token_payload.get("preferred_username", "")

        user_session_name = REFRESH_TOKEN_KEY.format(user=user)
        user_sessions = self.storage.map_getall(user_session_name)

        if self.blacklist.check():
            raise ApiUnauthorized(description="Access token is not valid")

        if auth_provider == AuthProvider.KEYCLOAK:
            keycloak_openid.logout(self.refresh_token)

        self.blacklist.add()

        if self.refresh_token not in user_sessions.keys():
            raise ApiUnauthorized(description="User not authorized")

        del user_sessions[self.refresh_token]

        if not user_sessions:
            self.storage.delete(user_session_name)
        else:
            self.storage.map_delete(user_session_name, self.refresh_token)

        return {"message": "Logged out"}, 200
