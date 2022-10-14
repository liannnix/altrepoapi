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
import hashlib
import ldap
import base64

from collections import namedtuple

from altrepo_api.settings import namespace
from altrepo_api.utils import get_logger

logger = get_logger(__name__)

AuthCheckResult = namedtuple("AuthCheckResult", ["verified", "error", "value"])


def check_auth(token, ldap_group: str):
    try:
        token = token.split()[1].strip()
        user, password = base64.b64decode(token).decode("utf-8").split(":")
    except Exception:
        logger.error("Authorization token validation error")
        return AuthCheckResult(False, "token validation error", {})

    logger.info(f"User '{user}' attempt to authorize")

    if ldap_group is not None:
        return check_auth_ldap(user, password, ldap_group)
    else:
        return check_auth_base(user, password)


def check_auth_base(user, password):
    passwd_hash = hashlib.sha512(password.encode("utf-8")).hexdigest()
    if user == namespace.ADMIN_USER and passwd_hash == namespace.ADMIN_PASSWORD:
        logger.info(f"User '{user}' successfully authorized")
        return AuthCheckResult(True, "OK", {"user": user})
    else:
        logger.warning(f"User '{user}' authorization failed")
        return AuthCheckResult(False, "authorization failed", {})


def check_auth_ldap(user, password, ldap_group):
    try:
        # build a client
        ldap_client = ldap.initialize(namespace.AUTH_LDAP_SERVER_URI, bytes_mode=False)
    except ldap.SERVER_DOWN:
        return AuthCheckResult(False, "Can't connection ldap server", {})

    try:
        # binds to the LDAP server with the user's DN and password
        ldap_client.simple_bind_s(
            namespace.AUTH_LDAP_USER_SEARCH % {"user": user}, password
        )
    except ldap.INVALID_CREDENTIALS:
        return AuthCheckResult(
            False, "Authorization failed: invalid login or password", {}
        )
    else:
        # Returns True if the group requirement (AUTH_LDAP_REQUIRE_GROUP) is met
        try:
            is_member = ldap_client.compare_s(
                namespace.AUTH_LDAP_REQUIRE_GROUP % {"group": ldap_group},
                "member",
                namespace.AUTH_LDAP_USER_SEARCH % {"user": user},
            )
        except ldap.PROTOCOL_ERROR:
            return AuthCheckResult(False, f"Group {ldap_group} does not exist", {})
        if is_member:
            return AuthCheckResult(True, "OK", {"user": user})
        else:
            return AuthCheckResult(
                False, "user does not satisfy AUTH_LDAP_REQUIRE_GROUP", {}
            )
