from os import name
from flask import Blueprint, g
from flask_restx import Resource, abort
from api.restplus import api
from utils import get_logger, url_logging

from api.package.parsers import package_info_args, pkg_build_dep_args
from api.package.serializers import package_info_model
from api.package.endpoints.package_info import PackageInfo
from api.package.endpoints.pkg_build_dependency import PackageBuildDependency


logger = get_logger(__name__)

task_bp = Blueprint('package', __name__)

ns = api.namespace('package', description="Packages information API")


@ns.route('/package_info/<string:pkg>',
    doc={
        'params': {'pkg': 'package name'},
        'description': "get information for package by name",
        'responses': {
            200: 'Success',
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routePackageInfo(Resource):
    @ns.expect(package_info_args)
    @ns.marshal_with(package_info_model, as_list=True)
    def get(self, pkg):
        args = package_info_args.parse_args()
        url_logging(logger, g.url)
        # pkg_info = PackageInfo(g.connection, id, args['try'], args['iteration'])
        pkg_info = PackageInfo(g.connection, pkg, args['pkg_hash'])
        if not pkg_info.check_package():
            abort(404, message=f"Package '{pkg}' not found in database", package=pkg)
        if not pkg_info.check_params():
            abort(400, message=f"Request parameters validation failed", args=args)
        result, code =  pkg_info.get()
        if code != 200:
            abort(code, message="Error occured during request handeling", details=result)
        return result, code


@ns.route('/build_dependency/',
    doc={
        'description': "get packages build dependencies",
        'responses': {
            400: 'Request parameters validation error',
            404: 'Requested data not found in database'
        }
    }
)
class routePackageBuildDependency(Resource):
    @ns.expect(pkg_build_dep_args)
    # @ns.marshal_with(pkg_build_dep_model)
    def get(self):
        args = pkg_build_dep_args.parse_args()
        url_logging(logger, g.url)
        pkg_build_dep = PackageBuildDependency(g.connection, **args)
        if not pkg_build_dep.check_params():
            abort(400, 
            message=f"Request parameters validation error",
            args=args,
            validation_message=pkg_build_dep.validation_results)
        return pkg_build_dep.get()
