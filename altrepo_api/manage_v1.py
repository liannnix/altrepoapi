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

from flask import Blueprint
from flask_restx import Api

from altrepo_api.api.management import ns as management_ns
from altrepo_api.api.auth import ns as auth_ns


VERSION = "0.0.1"

authorizations = {
    "BasicAuth": {"type": "basic", "in": "header", "name": "Authorization"},
    "Bearer": {"type": "apiKey", "in": "header", "name": "Authorization"},
}

blueprint = Blueprint("manage", __name__, url_prefix="/manage")

api = Api(
    blueprint,
    version=VERSION,
    title="ALTRepo vulnerability management API",
    license="GNU AGPLv3",
    license_url="https://www.gnu.org/licenses/agpl-3.0.en.html",
    description="altrepo API v1",
    # default="manage",
    default_label="basic functions",
    authorizations=authorizations,
)

api.add_namespace(auth_ns)
api.add_namespace(management_ns)
