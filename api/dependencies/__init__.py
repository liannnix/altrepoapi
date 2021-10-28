from flask import g
from flask_restx import Resource, abort, Namespace

from utils import get_logger, url_logging, response_error_parser
from api.dependencies.endpoints.dependecy_info import (
    DependsBinPackage,
    PackagesDependence,
)

ns = Namespace("dependencies", description="dependencies information API")

from api.dependencies.parsers import pkgs_depends_args
from api.dependencies.serializers import (
    package_dependencies_model,
    depends_packages_model,
)

logger = get_logger(__name__)


@ns.route(
    "/binary_package_dependencies/<int:pkghash>",
    doc={
        "description": "Get binary package dependencies",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeDependsBinPakage(Resource):
    @ns.expect()
    @ns.marshal_with(package_dependencies_model)
    def get(self, pkghash):
        args = {}
        url_logging(logger, g.url)
        wrk = DependsBinPackage(g.connection, pkghash)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/packages_by_dependency",
    doc={
        "description": "Get binary packages by dependency name and type",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackageDepends(Resource):
    @ns.expect(pkgs_depends_args)
    @ns.marshal_with(depends_packages_model)
    def get(self):
        args = pkgs_depends_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackagesDependence(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code
