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

import base64
import datetime
import hashlib
import jwt

from flask import Request, request
from typing import Any, NamedTuple, Optional, Protocol, Union

from altrepo_api.settings import namespace
from .redis import RedisStorage
from .file_storage import FileStorage
from ..constants import BLACKLISTED_ACCESS_TOKEN_KEY, JWT_ENCODE_ALGORITHM


# define `STORAGE` using `namespace.TOKEN_STORAGE` value
if namespace.TOKEN_STORAGE == "file":
    STORAGE = FileStorage()
elif namespace.TOKEN_STORAGE == "redis":
    STORAGE = RedisStorage(namespace.REDIS_URL)
else:
    raise ValueError(f"Unknown token storage type: {namespace.TOKEN_STORAGE}")


class InvalidTokenError(Exception):
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
        payload=payload, key=namespace.ADMIN_PASSWORD, algorithm=JWT_ENCODE_ALGORITHM
    )


def decode_jwt_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            jwt=token, key=namespace.ADMIN_PASSWORD, algorithms=[JWT_ENCODE_ALGORITHM]
        )
    except (jwt.PyJWTError, jwt.DecodeError):
        raise InvalidTokenError("Invalid token")


def user_fingerprint(request: Request) -> str:
    """
    Get user fingerprint MD5 hash based on ip, user-agent and accept-language.
    """

    user_info = "|".join(
        [
            str(request.remote_addr),
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

    return jwt.encode(payload, namespace.ADMIN_PASSWORD, algorithm="HS256")


def check_fingerprint(fingerprint: str) -> bool:
    """
    Verifies if request context user's fingerprint is equal to given one.
    """
    current_fingerprint = user_fingerprint(request)
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
        if the fingerprint of the current user does not
        match the fingerprint of the access token, then
        add the token to the blacklist.
        """

        if self.get():
            return True

        token_payload = decode_jwt_token(self.token)
        saved_fingerprint = token_payload.get("fingerprint", "")

        return not self._check_fingerprint(saved_fingerprint)

    def _check_fingerprint(self, fingerprint: str) -> bool:
        """
        Check the fingerprint of the current user and
        the fingerprint of the access token.
        """

        if fingerprint != user_fingerprint(request):
            self.add()
            return False

        return True
