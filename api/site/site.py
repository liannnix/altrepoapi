from flask import g
from flask_restx import Resource, abort, Namespace

from utils import get_logger, url_logging, response_error_parser

from .endpoints.package_info import PackageInfo, PackageChangelog
from .endpoints.pkgset_packages import PackagesetPackages

ns = Namespace('site', description="web site API")

from .parsers import pkgset_packages_args, package_chlog_args, package_info_args
from .serializers import pkgset_packages_model, package_chlog_model, package_info_model

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
        pkg= PackagesetPackages(g.connection, **args)
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
        pkg = PackageChangelog(g.connection, pkghash, **args)
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
        pkg = PackageInfo(g.connection, pkghash, **args)
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
