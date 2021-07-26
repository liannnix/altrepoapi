from flask import g
from flask_restx import Resource, abort, Namespace

from utils import get_logger, url_logging, response_error_parser

from .endpoints.package_info import PackageInfo, PackageChangelog, AllPackageArchs
from .endpoints.pkgset_packages import PackagesetPackages, PackagesetPackageHash
from .endpoints.pkgset_packages import PackagesetFindPackages, AllPackagesets
from .endpoints.task_info import TasksByPackage

ns = Namespace('site', description="web site API")

from .parsers import pkgset_packages_args, package_chlog_args, package_info_args
from .parsers import pkgset_pkghash_args, task_by_name_args, pkgs_by_name_args
from .serializers import pkgset_packages_model, package_chlog_model, package_info_model
from .serializers import pkgset_pkghash_model, task_by_name_model, fing_pkgs_by_name_model
from .serializers import all_pkgsets_model, all_archs_model

logger = get_logger(__name__)


@ns.route('/repository_packages',
    doc={
        'description': ("Get list of packageset packages in accordance "
            "to given parameters"),
        'responses': {
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routePackagesetPackages(Resource):
    @ns.expect(pkgset_packages_args)
    @ns.marshal_with(pkgset_packages_model)
    def get(self):
        args = pkgset_packages_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk= PackagesetPackages(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results
                )
        result, code =  wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/package_changelog/<int:pkghash>',
    doc={
        'params': {'pkghash': 'package hash'},
        'description': "Get package changelog history by hash",
        'responses': {
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routePackageChangelog(Resource):
    pass
    @ns.expect(package_chlog_args)
    @ns.marshal_with(package_chlog_model)
    def get(self, pkghash):
        args = package_chlog_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageChangelog(g.connection, pkghash, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results
                )
        result, code =  wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/package_info/<int:pkghash>',
    doc={
        'params': {'pkghash': 'package hash'},
        'description': "Get package info by hash",
        'responses': {
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routePackageInfo(Resource):
    pass
    @ns.expect(package_info_args)
    @ns.marshal_with(package_info_model)
    def get(self, pkghash):
        args = package_info_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageInfo(g.connection, pkghash, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results
                )
        result, code =  wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/pkghash_by_name',
    doc={
        'description': ("Get source package hash by package name and "
            "package set name"),
        'responses': {
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routePackagesetPackageHash(Resource):
    @ns.expect(pkgset_pkghash_args)
    @ns.marshal_with(pkgset_pkghash_model)
    def get(self):
        args = pkgset_pkghash_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk= PackagesetPackageHash(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results
                )
        result, code =  wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/tasks_by_package',
    doc={
        'description': "Get tasks list by source package name",
        'responses': {
            400: 'Request parameters validation error',
            404: 'Data not found in database'
        }
    }
)
class routeTasksByPackage(Resource):
    @ns.expect(task_by_name_args)
    @ns.marshal_with(task_by_name_model)
    def get(self):
        args = task_by_name_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk= TasksByPackage(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results
                )
        result, code =  wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/find_packages',
    doc={
        'description': "Find packages by name",
        'responses': {
            400: 'Request parameters validation error',
            404: 'Data not found in database'
        }
    }
)
class routePackagesetFindPackages(Resource):
    @ns.expect(pkgs_by_name_args)
    @ns.marshal_with(fing_pkgs_by_name_model)
    def get(self):
        args = pkgs_by_name_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk= PackagesetFindPackages(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results
                )
        result, code =  wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/all_pkgsets',
    doc={
        'description': "Get package sets list",
        'responses': {
            404: 'Data not found in database'
        }
    }
)
class routeAllPackagesets(Resource):
    # @ns.expect()
    @ns.marshal_with(all_pkgsets_model)
    def get(self):
        args = {}
        url_logging(logger, g.url)
        wrk= AllPackagesets(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results
                )
        result, code =  wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route('/all_pkgs_archs',
    doc={
        'description': "Get binary package archs list",
        'responses': {
            404: 'Data not found in database'
        }
    }
)
class routeAllPackageArchs(Resource):
    # @ns.expect()
    @ns.marshal_with(all_archs_model)
    def get(self):
        args = {}
        url_logging(logger, g.url)
        wrk= AllPackageArchs(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results
                )
        result, code =  wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code
