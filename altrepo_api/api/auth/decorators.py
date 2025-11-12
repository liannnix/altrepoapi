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

from datetime import datetime, UTC
from functools import wraps
from typing import Any, Optional, Union

from flask import g, request
from keycloak import KeycloakError

from altrepo_api.settings import AccessGroups, namespace
from altrepo_api.utils import get_logger

from .auth import check_auth, find_max_ranked_group_by_roles
from .constants import AuthProvider
from .exceptions import ApiForbidden, ApiUnauthorized
from .keycloak import keycloak_openid
from .token import (
    AccessTokenBlacklist,
    ExpiredTokenError,
    InvalidTokenError,
    UserRolesCache,
    decode_jwt_token,
    token_user_name,
    token_user_display_name
)


def auth_required(
    _func=None,
    *,
    ldap_groups: list[AccessGroups] = [],
    keycloak_roles: Optional[list[str]] = None,
    admin_only=False,
):
    def _auth_required(func):
        """Execute function if request contains valid access token."""

        @wraps(func)
        def decorated(*args, **kwargs):
            _ = _check_access_auth(
                admin_only=admin_only,
                ldap_groups=ldap_groups,
                keycloak_roles=keycloak_roles,
            )
            return func(*args, **kwargs)

        return decorated

    if _func is None:
        return _auth_required
    else:
        return _auth_required(_func)


def _check_access_auth(
    admin_only: bool = False,
    ldap_groups: list[AccessGroups] = [],
    keycloak_roles: Optional[list[str]] = None,
) -> dict[str, Any]:
    token = request.headers.get("Authorization")

    if not token:
        raise ApiUnauthorized(description="Unauthorized", admin_only=admin_only)

    result = check_auth(
        token,
        ldap_groups=[namespace.ACCESS_GROUPS[group] for group in ldap_groups],
        keycloak_roles=keycloak_roles,
    )

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


def token_required(role: str, *, validate_role=True):
    def _token_required(func):
        """Execute function if request contains valid access token."""

        @wraps(func)
        def decorated(*args, **kwargs):
            token_payload = _check_access_token(role, validate_role)
            for name, val in token_payload.items():
                setattr(decorated, name, val)
            return func(*args, **kwargs)

        return decorated

    return _token_required


def _check_access_token(role: str, validate_role: bool) -> dict[str, Any]:
    token = request.headers.get("Authorization")
    if not token:
        raise ApiUnauthorized(description="Authentication token is required")

    try:
        auth_provider, token_payload = decode_jwt_token(token)
    except InvalidTokenError:
        raise ApiUnauthorized(description="Invalid token")
    except ExpiredTokenError:
        raise ApiUnauthorized(description="Token expired")

    expires_at: int = token_payload["exp"]

    if AccessTokenBlacklist(token, expires_at).check():
        raise ApiUnauthorized(description="Token blacklisted")

    user_name: str = token_user_name(auth_provider, token_payload)
    user_display_name: str = token_user_display_name(auth_provider, token_payload)
    user_group: Union[str, None] = None
    user_roles: list[str] = []

    users_cache = UserRolesCache(conn=g.connection, logger=get_logger(__name__))
    cached_user = users_cache.get(user_name)

    if cached_user:
        user_roles = cached_user.get("roles", [])

        if validate_role and role not in user_roles:
            raise ApiForbidden()

        return {"token": token, "exp": expires_at}

    if auth_provider == AuthProvider.LDAP:
        user_roles = token_payload.get("roles", [])

    elif auth_provider == AuthProvider.KEYCLOAK:
        try:
            keycloak_openid.userinfo(token)
        except KeycloakError as e:
            raise ApiUnauthorized(f"Keycloak token validation error: {e}")

        user_roles = (
            token_payload.get("resource_access", {})
            .get(namespace.KEYCLOAK_CLIENT_ID, {})
            .get("roles", [])
        )
    else:
        raise ApiUnauthorized(description="Authentication provider is unknown")

    if validate_role and role not in user_roles:
        raise ApiForbidden()

    user_group = find_max_ranked_group_by_roles(user_roles)
    if user_group is None:
        raise ApiForbidden()

    delta = int(
        (
            datetime.fromtimestamp(expires_at, tz=UTC) - datetime.now(tz=UTC)
        ).total_seconds()
    )

    users_cache.add(
        user=user_name,
        display_name=user_display_name,
        group=user_group,
        roles=user_roles,
        expires_in=(delta if delta > 0 else 1),
    )

    return {"token": token, "exp": expires_at}
