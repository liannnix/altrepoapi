# ALTRepo API
# Copyright (C) 2021-2023 BaseALT Ltd

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

from typing import Any, NamedTuple

from .token.token import parse_basic_auth_token, InvalidTokenError

from altrepo_api.settings import namespace
from altrepo_api.utils import get_logger

logger = get_logger(__name__)


class AuthCheckResult(NamedTuple):
    verified: bool
    error: str
    value: dict[str, Any]


def check_auth(token: str, ldap_groups: list[str]) -> AuthCheckResult:
    try:
        credentials = parse_basic_auth_token(token)
    except InvalidTokenError:
        logger.error("Authorization token validation error")
        return AuthCheckResult(False, "token validation error", {})

    logger.info(f"User '{credentials.user}' attempt to authorize")

    if ldap_groups:
        return check_auth_ldap(credentials.user, credentials.password, ldap_groups)
    else:
        return check_auth_basic(credentials.user, credentials.password)


def check_auth_basic(user: str, password: str) -> AuthCheckResult:
    passwd_hash = hashlib.sha512(password.encode("utf-8")).hexdigest()

    if user == namespace.ADMIN_USER and passwd_hash == namespace.ADMIN_PASSWORD:
        logger.info(f"User '{user}' successfully authorized")
        return AuthCheckResult(True, "OK", {"user": user})
    else:
        logger.warning(f"User '{user}' authorization failed")
        return AuthCheckResult(False, "authorization failed", {})


def check_auth_ldap(
    user: str, password: str, ldap_groups: list[str]
) -> AuthCheckResult:
    try:
        # build a client
        ldap_client = ldap.initialize(namespace.LDAP_SERVER_URI, bytes_mode=False)
    except ldap.SERVER_DOWN:  # type: ignore
        return AuthCheckResult(False, "LDAP server connection failed", {})

    def is_member_of_ldap_group(group: str) -> bool:
        user_dn = namespace.LDAP_USER_SEARCH % {"user": user}
        group_dn = namespace.LDAP_REQUIRE_GROUP % {"group": group}
        filter = f"(memberOf={group_dn})"
        # Returns True if the group requirement (AUTH_LDAP_REQUIRE_GROUP) is met
        res = ldap_client.search_ext_s(user_dn, ldap.SCOPE_SUBTREE, filter) != []  # type: ignore
        if res:
            return res
        # fall back to direct group memebership matching
        return ldap_client.compare_s(group_dn, "member", user_dn)

    try:
        # binds to the LDAP server with the user's DN and password
        ldap_client.simple_bind_s(namespace.LDAP_USER_SEARCH % {"user": user}, password)
    except ldap.INVALID_CREDENTIALS:  # type: ignore
        logger.warning(f"User '{user}' LDAP authentication failed")
        return AuthCheckResult(False, "LDAP authentication failed", {})
    else:
        # checks whether user a memberof any groups provided
        user_groups = []
        for group in ldap_groups:
            try:
                if is_member_of_ldap_group(group):
                    user_groups.append(group)
            except (ldap.NO_SUCH_ATTRIBUTE, ldap.NO_SUCH_OBJECT, ldap.PROTOCOL_ERROR):  # type: ignore
                logger.info(f"No such group `{group}` found for `{user}`")
                pass

        if user_groups:
            logger.info(f"User '{user}' successfully authorized with LDAP")
            return AuthCheckResult(True, "OK", {"user": user, "groups": user_groups})
        else:
            logger.warning(f"User '{user}' LDAP authorization failed")
            return AuthCheckResult(False, "LDAP authorization failed", {})
