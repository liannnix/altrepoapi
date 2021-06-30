from flask import g
from flask_restx import Resource, abort, Namespace

from utils import get_logger, url_logging, response_error_parser

from .endpoints.package_info import PackageInfo
from .endpoints.pkg_build_dependency import PackageBuildDependency
from .endpoints.misconflict_packages import PackageMisconflictPackages
from .endpoints.find_packageset import FindPackageset
from .endpoints.package_by_file import PackageByFileName, PackageByFileMD5
from .endpoints.dependent_packages import DependentPackages
from .endpoints.unpackaged_dirs import UnpackagedDirs
from .endpoints.build_dependency_set import PackageBuildDependencySet

ns = Namespace('package', description="Packages information API")

from .parsers import package_info_args, pkg_build_dep_args, misconflict_pkg_args
from .parsers import pkg_find_pkgset_args, pkg_by_file_name_args, pkg_by_file_md5_args
from .parsers import dependent_packages_args, unpackaged_dirs_args, build_dep_set_args
from .serializers import package_info_model, pkg_build_dep_model, misconflict_pkgs_model
from .serializers import pkg_find_pkgset_model, pkg_by_file_name_model
from .serializers import dependent_packages_model, unpackaged_dirs_args_model
from .serializers import build_dep_set_model

logger = get_logger(__name__)


@ns.route('/package_info',
    doc={
        'description': "Get information for package by parameters from last packages",
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
        pkg = PackageInfo(g.connection, **args)
        if not pkg.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=pkg.validation_results
                )
        result, code =  pkg.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/what_depends_src',
    doc={
        'description': "Get packages build dependencies by set of parameters",
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
        pkg = PackageBuildDependency(g.connection, **args)
        if not pkg.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=pkg.validation_results
                )
        result, code = pkg.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/misconflict',
    doc={
        'description': ("Get packages with conflicting files in packages "
            "that don't have a conflict in dependencies"),
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
        pkg = PackageMisconflictPackages(g.connection, **args)
        if not pkg.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=pkg.validation_results
                )
        result, code = pkg.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/find_packageset',
    doc={
        'description': ("Get information about packages from package sets "
            "by given source packages list"),
        'responses': {
            400: 'Request parameters validation error',
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
        pkg= FindPackageset(g.connection, **args)
        if not pkg.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=pkg.validation_results
                )
        result, code =  pkg.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/package_by_file_name',
    doc={
        'description': ("Get information about packages from  last package sets "
            "by given file name and package set name."
            "\nFile name wildcars '*' is allowed."),
        'responses': {
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routePackageByFileName(Resource):
    @ns.expect(pkg_by_file_name_args)
    @ns.marshal_with(pkg_by_file_name_model)
    def get(self):
        args = pkg_by_file_name_args.parse_args(strict=True)
        url_logging(logger, g.url)
        pkg= PackageByFileName(g.connection, **args)
        if not pkg.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=pkg.validation_results
                )
        result, code =  pkg.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/package_by_file_md5',
    doc={
        'description': ("Get information about packages from  last package sets "
            "by given file MD5 checksum and package set name"),
        'responses': {
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routePackageByFileMD5(Resource):
    @ns.expect(pkg_by_file_md5_args)
    @ns.marshal_with(pkg_by_file_name_model)
    def get(self):
        args = pkg_by_file_md5_args.parse_args(strict=True)
        url_logging(logger, g.url)
        pkg= PackageByFileMD5(g.connection, **args)
        if not pkg.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=pkg.validation_results
                )
        result, code =  pkg.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/dependent_packages',
    doc={
        'description': ("Get information about packages whose binary packages "
            "depends on given package"),
        'responses': {
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routeDependentPackages(Resource):
    @ns.expect(dependent_packages_args)
    @ns.marshal_with(dependent_packages_model)
    def get(self):
        args = dependent_packages_args.parse_args(strict=True)
        url_logging(logger, g.url)
        pkg= DependentPackages(g.connection, **args)
        if not pkg.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=pkg.validation_results
                )
        result, code =  pkg.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/unpackaged_dirs',
    doc={
        'description': ("Get information about unpackaged directories "
            "by maintainer nickname"),
        'responses': {
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routeUnpackagedDirs(Resource):
    @ns.expect(unpackaged_dirs_args)
    @ns.marshal_with(unpackaged_dirs_args_model)
    def get(self):
        args = unpackaged_dirs_args.parse_args(strict=True)
        url_logging(logger, g.url)
        pkg= UnpackagedDirs(g.connection, **args)
        if not pkg.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=pkg.validation_results
                )
        result, code =  pkg.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/build_dependency_set',
    doc={
        'description': ("Get list of packages required for build by given "
            "packages list recursively"),
        'responses': {
            400: 'Request parameters validation error',
            404: 'Requested data not found in database'
        }
    }
)
class routePackageBuildDependencySet(Resource):
    @ns.expect(build_dep_set_args)
    @ns.marshal_with(build_dep_set_model)
    def get(self):
        args = build_dep_set_args.parse_args(strict=True)
        url_logging(logger, g.url)
        pkg = PackageBuildDependencySet(g.connection, **args)
        if not pkg.check_params():
            abort(
                400, 
                message=f"Request parameters validation error",
                args=args,
                validation_message=pkg.validation_results
                )
        result, code = pkg.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code
