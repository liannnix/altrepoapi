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
from flask_restx import Api
from flask_restx import Resource, fields

from altrepo_api.version import __version__
from altrepo_api.settings import namespace as settings
from altrepo_api.api.auth.decorators import auth_required

from altrepo_api.api.acl import ns as acl_ns
from altrepo_api.api.bug import ns as bug_ns
from altrepo_api.api.task import ns as task_ns
from altrepo_api.api.task_progress import ns as task_progress_ns
from altrepo_api.api.package import ns as package_ns
from altrepo_api.api.packageset import ns as packageset_ns
from altrepo_api.api.dependencies import ns as dependencies_ns
from altrepo_api.api.image import ns as image_ns
from altrepo_api.api.files import ns as file_ns
from altrepo_api.api.export import ns as export_ns
from altrepo_api.api.license import ns as license_ns
from altrepo_api.api.site_task import ns as site_task_ns
from altrepo_api.api.site_image import ns as site_image_ns
from altrepo_api.api.site_package import ns as site_package_ns
from altrepo_api.api.site_pkgset_info import ns as site_pkgset_info
from altrepo_api.api.site_maintainer import ns as site_maintainer_ns
from altrepo_api.api.site_packageset import ns as site_packageset_ns


authorizations = {
    "BasicAuth": {"type": "basic", "in": "header", "name": "Authorization"}
}

blueprint = Blueprint("api", __name__, url_prefix="/api")

api = Api(
    blueprint,
    version=__version__,
    title="ALTRepo API",
    license="GNU AGPLv3",
    license_url="https://www.gnu.org/licenses/agpl-3.0.en.html",
    description="altrepo API v1",
    default="api",
    default_label="basic functions",
    authorizations=authorizations,
)

# XXX: order is important here
api.add_namespace(task_ns)
api.add_namespace(task_progress_ns)
api.add_namespace(package_ns)
api.add_namespace(packageset_ns)
api.add_namespace(acl_ns)
api.add_namespace(bug_ns)
api.add_namespace(dependencies_ns)
api.add_namespace(image_ns)
api.add_namespace(file_ns)
api.add_namespace(export_ns)
api.add_namespace(license_ns)
api.add_namespace(site_task_ns)
api.add_namespace(site_image_ns)
api.add_namespace(site_package_ns)
api.add_namespace(site_pkgset_info)
api.add_namespace(site_maintainer_ns)
api.add_namespace(site_packageset_ns)

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


@api.route("/ping")
@api.doc(False)
class ApiPing(Resource):
    @api.doc(description="API authorization check")
    @api.doc(security="BasicAuth")
    @auth_required
    def get(self):
        return {"message": "pong"}, 200


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
