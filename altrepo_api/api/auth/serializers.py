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

from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()

auth_response_model = ns.model(
    "AuthResponseModel",
    {
        "access_token": fields.String(description="Access token", required=True),
        "refresh_token": fields.String(description="Refresh token", required=True),
    },
)

auth_logout_response_model = ns.model(
    "AuthLogoutResponseModel",
    {"message": fields.String(description="Logout message", required=True)},
)
