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

from keycloak import KeycloakError, KeycloakOpenID  # noqa: F401

from altrepo_api.settings import namespace

keycloak_openid = KeycloakOpenID(
    server_url=namespace.KEYCLOAK_SERVER_URL,
    verify=namespace.KEYCLOAK_SERVER_CHECK_SSL,
    realm_name=namespace.KEYCLOAK_REALM,
    client_id=namespace.KEYCLOAK_CLIENT_ID,
    client_secret_key=namespace.KEYCLOAK_CLIENT_SECRET_KEY,
)
