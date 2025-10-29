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
import time
from typing import NamedTuple
from uuid import uuid4

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.settings import namespace, AccessGroups
from altrepo_api.utils import get_logger

from ..auth import check_auth_keycloak, check_auth_ldap, find_max_ranked_group
from ..constants import REFRESH_TOKEN_KEY, AuthProvider
from ..token import STORAGE, encode_jwt_token, user_fingerprint

logger = get_logger(__name__)


class AuthLoginArgs(NamedTuple):
    nickname: str
    password: str
    auth_provider: AuthProvider


class AuthLogin(APIWorker):
    """Authenticates an existing user and return an access and refresh tokens."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.kwargs = kwargs
        self.args: AuthLoginArgs
        self.storage = STORAGE
        self._token = ""
        super().__init__()

    def check_params_post(self) -> bool:
        auth_provider = self.kwargs["auth_provider"]

        if auth_provider not in AuthProvider:
            self.validation_results.append(
                f"Unknown authorization provider: {auth_provider}"
            )

        self.args = AuthLoginArgs(
            nickname=self.kwargs["nickname"],
            password=self.kwargs["password"],
            auth_provider=AuthProvider(auth_provider),
        )

        return self.validation_results == []

    def post(self) -> WorkerResult:
        match self.args.auth_provider:
            case AuthProvider.LDAP:
                return self.ldap_auth()
            case AuthProvider.KEYCLOAK:
                return self.keycloak_auth()

    def keycloak_auth(self) -> WorkerResult:
        auth_result = check_auth_keycloak(self.args.nickname, self.args.password)

        if auth_result.verified is False:
            return {"message": auth_result.error}, 401

        access_token: str = auth_result.value["access_token"]
        refresh_token: str = auth_result.value["refresh_token"]
        refresh_expires_in: int = auth_result.value["refresh_expires_in"]

        self.add_refresh_session(
            refresh_token=refresh_token,
            refresh_expires_in=refresh_expires_in,
        )

        response = {"access_token": access_token, "refresh_token": refresh_token}
        headers = {
            "Set-Cookie": (
                f"refresh_token={refresh_token}; Expires=f'{refresh_expires_in}'; "
                f"{namespace.AUTH_COOKIES_OPTIONS}"
            )
        }

        return response, 200, headers

    def ldap_auth(self) -> WorkerResult:
        auth_result = check_auth_ldap(
            self.args.nickname,
            self.args.password,
            list(namespace.ACCESS_GROUPS.values()),
        )

        if auth_result.verified is False:
            return {"message": auth_result.error}, 401

        access_groups = auth_result.value["groups"]

        def AG_REVERSED_LUT(group) -> set[AccessGroups]:
            groups = set()
            for k, v in namespace.ACCESS_GROUPS.items():
                if v == group:
                    groups.add(k)
            return groups

        # collect KeyCloak-wise groups and roles from  LDAP Access Groups mappings
        user_groups = set()
        user_roles = set()
        for group in access_groups:
            for g in AG_REVERSED_LUT(group):
                if g in namespace.AG_GROUP_MAPPING:
                    user_groups.update(namespace.AG_GROUP_MAPPING[g])
                if g in namespace.AG_ROLE_MAPPING:
                    user_roles.update(namespace.AG_ROLE_MAPPING[g])
        user_groups = sorted(user_groups)
        user_roles = sorted(user_roles)

        refresh_token = str(uuid4())
        refresh_expires_in = namespace.EXPIRES_REFRESH_TOKEN

        cookie_expires = (
            datetime.datetime.now() + datetime.timedelta(seconds=refresh_expires_in)
        ).ctime()

        token_expires = datetime.datetime.now(
            tz=datetime.timezone.utc
        ) + datetime.timedelta(seconds=namespace.EXPIRES_ACCESS_TOKEN)

        fingerprint = self.add_refresh_session(
            refresh_token=refresh_token,
            refresh_expires_in=refresh_expires_in,
        )

        if not refresh_token:
            logger.warning("Refresh token is None")
            return {"message": "Unauthorized"}, 401

        access_token = encode_jwt_token(
            {
                "nickname": self.args.nickname,
                "fingerprint": fingerprint,
                "exp": token_expires,
                "ns": time.perf_counter_ns(),
                "group": find_max_ranked_group(user_groups),
                "roles": user_roles,
                "provider": self.args.auth_provider.value,
            }
        )

        response = {"access_token": access_token, "refresh_token": refresh_token}
        headers = {
            "Set-Cookie": (
                f"refresh_token={refresh_token}; Expires=f'{cookie_expires}'; "
                f"{namespace.AUTH_COOKIES_OPTIONS}"
            )
        }

        return response, 200, headers

    def add_refresh_session(self, refresh_token: str, refresh_expires_in: int):
        """
        Adds new session if stored user sessions does not exceeds MAX_REFRESH_SESSIONS_COUNT,
        else remove all user sessions and create a new session.
        """
        fingerprint = user_fingerprint()
        user_session_name = REFRESH_TOKEN_KEY.format(user=self.args.nickname)

        if self._exceeds_max_sessions(user_session_name):
            self.storage.delete(user_session_name)

        self._add_refresh_session(
            fingerprint,
            user_session_name,
            refresh_token,
            refresh_expires_in,
        )

        return fingerprint

    def _exceeds_max_sessions(self, user_session_name: str) -> bool:
        """
        Checks the number of sessions with the same user nickname.
        """
        user_sessions = self.storage.map_getall(user_session_name)
        return len(user_sessions.keys()) >= namespace.MAX_REFRESH_SESSIONS_COUNT

    def _add_refresh_session(
        self,
        fingerprint: str,
        user_session_name: str,
        refresh_token: str,
        refresh_expires_in: int,
    ):
        """
        Adds session to the storage, if the session exists, raises an exception.
        """
        user_sessions = self.storage.map_getall(self._token)
        active_fingerprints = {
            json.loads(el).get("fingerprint", None) for el in user_sessions.values()
        }

        if fingerprint not in active_fingerprints:
            new_refresh_session = {
                refresh_token: json.dumps(
                    {
                        "nickname": self.args.nickname,
                        "fingerprint": fingerprint,
                        "expires": refresh_expires_in,
                        "create_at": int(datetime.datetime.now().timestamp()),
                    }
                )
            }

            self.storage.map_set(
                user_session_name, new_refresh_session, refresh_expires_in
            )

        for key, values in user_sessions.items():
            if fingerprint == json.loads(values)["fingerprint"]:
                return key
