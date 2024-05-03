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

from flask import Blueprint, send_from_directory
from flask_restx import Api, Resource, fields

from altrepo_api.api.management import ns as management_ns, __version__ as VERSION
from altrepo_api.api.auth import ns as auth_ns
from altrepo_api.settings import namespace as settings


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
    description="ALTRepo API v1",
    default="basic",
    default_label="basic functions",
    authorizations=authorizations,
)

api.add_namespace(auth_ns)
api.add_namespace(management_ns)

version_fields = api.model(
    "APIVersion",
    {
        "name": fields.String(attribute="title", description="API name"),
        "version": fields.String(description="API version"),
        "description": fields.String(description="API description"),
    },
)


@api.route("/version")
@api.doc(description="get API version")
class ApiVersion(Resource):
    @api.marshal_with(version_fields)
    def get(self):
        return api, 200


@api.route("/license")
@api.doc(description="get license")
class ApiLicense(Resource):
    @api.produces(["text/plain"])
    def get(self):
        licenseFile = "static/LICENSE"
        return send_from_directory(
            settings.PROJECT_DIR,
            licenseFile,
            as_attachment=False,
            mimetype="text/plain",
        )
