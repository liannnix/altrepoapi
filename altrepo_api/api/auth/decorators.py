# ALTRepo API
# Copyright (C) 2021-2025 BaseALT Ltd

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

from functools import wraps
from flask import request
from typing import Any

from .auth import check_auth
from .exceptions import ApiUnauthorized, ApiForbidden
from .token.token import AccessTokenBlacklist, InvalidTokenError, decode_jwt_token

from altrepo_api.settings import namespace, AccessGroups


def auth_required(
    _func=None, *, ldap_groups: list[AccessGroups] = [], admin_only=False
):
    def _auth_required(func):
        """Execute function if request contains valid access token."""

        @wraps(func)
        def decorated(*args, **kwargs):
            _ = _check_access_auth(admin_only=admin_only, ldap_groups=ldap_groups)
            return func(*args, **kwargs)

        return decorated

    if _func is None:
        return _auth_required
    else:
        return _auth_required(_func)


def _check_access_auth(
    admin_only: bool = False, ldap_groups: list[AccessGroups] = []
) -> dict[str, Any]:
    token = request.headers.get("Authorization")

    if not token:
        raise ApiUnauthorized(description="Unauthorized", admin_only=admin_only)

    result = check_auth(token, [namespace.ACCESS_GROUPS[g] for g in ldap_groups])

    if not result.verified:
        raise ApiUnauthorized(
            description=result.error,
            admin_only=admin_only,
            error="Authorization error",
            error_description=result.error,
        )

    if (
        admin_only
        and not result.value.get("user", "_NOT_FOUND_") == namespace.ADMIN_USER
    ):
        raise ApiForbidden("You are not an administrator")

    return result.value


def token_required(ldap_groups: list[AccessGroups]):
    def _token_required(func):
        """Execute function if request contains valid access token."""

        @wraps(func)
        def decorated(*args, **kwargs):
            token_payload = _check_access_token(ldap_groups)
            for name, val in token_payload.items():
                setattr(decorated, name, val)
            return func(*args, **kwargs)

        return decorated

    return _token_required


def _check_access_token(ldap_groups: list[AccessGroups]) -> dict[str, Any]:
    token = request.headers.get("Authorization")
    if not token:
        raise ApiUnauthorized(description="Authentication token is required")

    try:
        token_payload = decode_jwt_token(token)
    except InvalidTokenError:
        raise ApiUnauthorized(description="Invalid token.")

    if AccessTokenBlacklist(token, int(token_payload["exp"])).check():
        raise ApiUnauthorized(description="Token blacklisted")

    # check if user groups from token is intersects with given LDAP groups
    user_ldap_groups = set(token_payload.get("groups", []))

    if not user_ldap_groups or not user_ldap_groups.intersection(
        namespace.ACCESS_GROUPS[g] for g in ldap_groups
    ):
        raise ApiForbidden()

    return {"token": token, "exp": token_payload.get("exp")}
