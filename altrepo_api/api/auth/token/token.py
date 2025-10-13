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

import base64
import datetime
import hashlib
import jwt
import jwcrypto.jwt
import time

from flask import request
from typing import Any, NamedTuple, Optional, Protocol, Union

from altrepo_api.settings import namespace
from altrepo_api.utils import get_real_ip
from .redis import RedisStorage
from .file_storage import FileStorage
from ..constants import BLACKLISTED_ACCESS_TOKEN_KEY, JWT_ENCODE_ALGORITHM, AuthProvider
from ..keycloak import keycloak_openid

# define `STORAGE` using `namespace.TOKEN_STORAGE` value
if namespace.TOKEN_STORAGE == "file":
    STORAGE = FileStorage()
elif namespace.TOKEN_STORAGE == "redis":
    STORAGE = RedisStorage(namespace.REDIS_URL)
else:
    raise ValueError(f"Unknown token storage type: {namespace.TOKEN_STORAGE}")


class InvalidTokenError(Exception):
    pass


class ExpiredTokenError(Exception):
    pass


class UserCredentials(NamedTuple):
    user: str
    password: str


class Storage(Protocol):
    def delete(self, name: str) -> None:
        """Deletes value from storage by name."""
        ...

    def map_delete(self, name: str, key: str) -> None:
        """Deletes value from mapping in storage by name and key."""
        ...

    def map_getall(self, name: str) -> dict[str, str]:
        """Retrives mapping from storage by name."""
        ...

    def map_get(self, name: str, key: str) -> Union[str, None]:
        """Retrives mapping value from storage by name and key."""
        ...

    def map_set(
        self,
        name: str,
        mapping: dict[str, Any],
        expire: Optional[int] = None,
    ) -> None:
        """Saves mapping to storage and set expiration time."""
        ...


def parse_basic_auth_token(token: str) -> UserCredentials:
    """Parse username and password from HTTP Authentication token."""

    try:
        return UserCredentials(
            *base64.b64decode(token.split()[1].strip()).decode("utf-8").split(":")
        )
    except Exception:
        raise InvalidTokenError("Invalid token")


def encode_jwt_token(payload: dict[str, Any]) -> str:
    return jwt.encode(
        payload=payload,
        key=namespace.ADMIN_PASSWORD,
        algorithm=JWT_ENCODE_ALGORITHM,
        headers={
            "typ": "JWT",
            "alg": JWT_ENCODE_ALGORITHM,
            "provider": AuthProvider.LDAP.value,
        },
    )


def decode_jwt_token(
    token: str, verify_exp: bool = True
) -> tuple[AuthProvider, dict[str, Any]]:
    try:
        header = jwt.get_unverified_header(token)

        if header.get("provider") == AuthProvider.LDAP:
            return AuthProvider.LDAP, jwt.decode(
                jwt=token,
                key=namespace.ADMIN_PASSWORD,
                algorithms=[JWT_ENCODE_ALGORITHM],
                options=None if verify_exp else {"verify_exp": False},
            )

        return AuthProvider.KEYCLOAK, keycloak_openid.decode_token(
            token, validate=verify_exp
        )

    except (jwt.PyJWTError, jwt.DecodeError):
        raise InvalidTokenError("Invalid token")
    except jwcrypto.jwt.JWTExpired:
        raise ExpiredTokenError("Token expired")


def user_fingerprint() -> str:
    """
    Get user fingerprint MD5 hash based on ip, user-agent and accept-language.
    """
    ip = get_real_ip()

    user_info = "|".join(
        [
            ip,
            str(request.user_agent),
            str(request.accept_languages),
        ]
    )

    return hashlib.md5(user_info.encode("utf-8")).hexdigest()


def update_access_token(payload: dict[str, Any]) -> str:
    """
    Updates JWT token payload `exp` field value and returns new encoded token.
    """
    payload["exp"] = datetime.datetime.now(
        tz=datetime.timezone.utc
    ) + datetime.timedelta(seconds=namespace.EXPIRES_ACCESS_TOKEN)
    payload["ns"] = time.perf_counter_ns()
    return encode_jwt_token(payload)


def check_fingerprint(fingerprint: str) -> bool:
    """
    Verifies if request context user's fingerprint is equal to given one.
    """
    current_fingerprint = user_fingerprint()
    return fingerprint == current_fingerprint


class AccessTokenBlacklist:
    def __init__(self, token: str, expires: int):
        self.token = token
        self.token_key = BLACKLISTED_ACCESS_TOKEN_KEY.format(token=token)
        self.expires = expires
        self.storage = STORAGE

    def add(self) -> None:
        self.storage.map_set(
            self.token_key, {"expires_at": self.expires}, namespace.EXPIRES_ACCESS_TOKEN
        )

    def get(self) -> dict[str, Any]:
        return self.storage.map_getall(self.token_key)

    def check(self) -> bool:
        """
        Check the access token in the blacklist.
        If the fingerprint of the current user does not
        match the fingerprint of the access token, then
        add the token to the blacklist.
        """

        if self.get():
            return True

        auth_provider, token_payload = decode_jwt_token(self.token)

        if auth_provider == AuthProvider.LDAP:
            if not check_fingerprint(token_payload.get("fingerprint", "")):
                self.add()
                return True

        return False
