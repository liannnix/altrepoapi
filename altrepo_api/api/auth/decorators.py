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
import jwt

from functools import wraps
from flask import request

from .endpoints.blacklisted_token import BlacklistedAccessToken
from .exceptions import ApiUnauthorized, ApiForbidden
from .auth import check_auth
from ...settings import namespace


def auth_required(_func=None, ldap_group=None):
    def _auth_required(f):
        """Execute function if request contains valid access token."""

        @wraps(f)
        def decorated(*args, **kwargs):
            token_payload = _check_access_auth(
                admin_only=False, ldap_group=ldap_group
            )  # noqa
            # for name, val in token_payload.items():
            #     setattr(decorated, name, val)
            return f(*args, **kwargs)

        return decorated

    if _func is None:
        # call with parameters
        return _auth_required
    else:
        # call without parameters
        return _auth_required(_func)


def admin_auth_required(f):
    """Execute function if request contains valid access token AND user is admin."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token_payload = _check_access_auth(admin_only=True)
        if not token_payload["admin"]:
            raise ApiForbidden()
        for name, val in token_payload.items():
            setattr(decorated, name, val)
        return f(*args, **kwargs)

    return decorated


def token_required(f):
    """Execute function if request contains valid access token."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token_payload = _check_access_token()
        for name, val in token_payload.items():
            setattr(decorated, name, val)
        return f(*args, **kwargs)

    return decorated


def _check_access_auth(admin_only=False, ldap_group=None):
    token = request.headers.get("Authorization")
    if not token:
        raise ApiUnauthorized(description="Unauthorized", admin_only=admin_only)
    result = check_auth(token, ldap_group)

    if not result.verified:
        raise ApiUnauthorized(
            description=result.error,
            admin_only=admin_only,
            error="invalid_token",
            error_description=result.error,
        )
    return result.value


def _check_access_token():
    token = request.headers.get("Authorization")
    if not token:
        raise ApiUnauthorized(
            description="Authentication Token is missing", admin_only=False
        )
    try:
        token_payload = jwt.decode(
            token, namespace.ADMIN_PASSWORD, algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        raise ApiUnauthorized("Access token expired.")
    except jwt.InvalidTokenError:
        raise ApiUnauthorized("Invalid token.")

    if BlacklistedAccessToken(
        token=token, expires=token_payload["exp"]
    ).check_blacklist():
        raise ApiUnauthorized("Token blacklisted.")
    token_payload["token"] = token
    return token_payload
