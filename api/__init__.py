from flask import Blueprint
from flask_restx import Api
from flask_restx import Resource, fields

from api.auth.decorators import auth_required

from .task.task import ns as task_ns
from .package.package import ns as package_ns
from .packageset.packageset import ns as packageset_ns
from .site.site import ns as site_ns
from .dependencies.dependencies import ns as dependencies_ns
from .bug.bug import ns as bug_ns


authorizations = {
    'BasicAuth': {
        'type': 'basic',
        'in': 'header',
        'name': 'Authorization'
    }
}

blueprint = Blueprint("api", __name__, url_prefix="/api")

api = Api(
    blueprint,
    version="1.3",
    title="altrepodb",
    description="altrepodb API",
    default="api",
    default_label="basic functions",
    authorizations=authorizations
)

api.add_namespace(task_ns)
api.add_namespace(package_ns)
api.add_namespace(packageset_ns)
api.add_namespace(bug_ns)
api.add_namespace(site_ns)
api.add_namespace(dependencies_ns)

version_fields = api.model(
    "APIVersion",
    {
        "name": fields.String(attribute="title", description="API name"),
        "version": fields.String(description="API version"),
        "description": fields.String(description="API description"),
    },
)


@api.route("/version")
class ApiVersion(Resource):
    @api.doc("get API information")
    @api.marshal_with(version_fields)
    def get(self):
        return api, 200


@api.route("/ping")
class ApiVersion(Resource):
    @api.doc("API ping")
    @api.doc(security="BasicAuth")
    @auth_required
    def get(self):
        return {"message": "pong"}, 200
