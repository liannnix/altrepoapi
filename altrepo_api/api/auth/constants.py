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

from enum import StrEnum

JWT_ENCODE_ALGORITHM = "HS256"
REFRESH_TOKEN_KEY = "refresh-token:{user}"
BLACKLISTED_ACCESS_TOKEN_KEY = "blacklisted:access-token:{token}"
USER_ROLES_KEY = "user:{user}"


class AuthProvider(StrEnum):
    LDAP = "ldap"
    KEYCLOAK = "keycloak"
