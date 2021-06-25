from flask import g
from flask_restx import Resource, abort, Namespace

from utils import get_logger, url_logging, response_error_parser

from .endpoints.package_info import PackageInfo
from .endpoints.pkg_build_dependency import PackageBuildDependency
from .endpoints.misconflict_packages import PackageMisconflictPackages
from .endpoints.find_packageset import FindPackageset

ns = Namespace('package', description="Packages information API")

from .parsers import package_info_args, pkg_build_dep_args, misconflict_pkg_args, pkg_find_pkgset_args
from .serializers import package_info_model, pkg_build_dep_model, misconflict_pkgs_model, pkg_find_pkgset_model

logger = get_logger(__name__)


@ns.route('/package_info/',
    doc={
        'description': "get information for package by parameters from last packages",
        'responses': {
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routePackageInfo(Resource):
    @ns.expect(package_info_args)
    @ns.marshal_with(package_info_model)
    def get(self):
        args = package_info_args.parse_args(strict=True)
        url_logging(logger, g.url)
        pkg_info = PackageInfo(g.connection, **args)
        if not pkg_info.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=pkg_info.validation_results
                )
        result, code =  pkg_info.get()
        if code != 200:
            abort(code, **response_error_parser(result))
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
    @ns.marshal_with(pkg_build_dep_model)
    def get(self):
        args = pkg_build_dep_args.parse_args(strict=True)
        url_logging(logger, g.url)
        pkg_build_dep = PackageBuildDependency(g.connection, **args)
        if not pkg_build_dep.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=pkg_build_dep.validation_results
                )
        result, code = pkg_build_dep.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/misconflict/',
    doc={
        'description': ("get packages with conflicting files in packages "
            "that do not have a conflict in dependencies"),
        'responses': {
            400: 'Request parameters validation error',
            404: 'Requested data not found in database'
        }
    }
)
class routePackageMisconflictPackages(Resource):
    @ns.expect(misconflict_pkg_args)
    @ns.marshal_with(misconflict_pkgs_model)
    def get(self):
        args = misconflict_pkg_args.parse_args(strict=True)
        url_logging(logger, g.url)
        misconflict_pkg = PackageMisconflictPackages(g.connection, **args)
        if not misconflict_pkg.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=misconflict_pkg.validation_results
                )
        result, code = misconflict_pkg.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/find_packageset',
    doc={
        'description': ("get information about packages from package sets "
            "by given source packages list"),
        'responses': {
            404: 'Package not found in database'
        }
    }
)
class routeFindPackageset(Resource):
    @ns.expect(pkg_find_pkgset_args)
    @ns.marshal_with(pkg_find_pkgset_model)
    def get(self):
        args = pkg_find_pkgset_args.parse_args(strict=True)
        url_logging(logger, g.url)
        pkg_set= FindPackageset(g.connection, **args)
        result, code =  pkg_set.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code
