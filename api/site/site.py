from flask import g
from flask_restx import Resource, abort, Namespace

from utils import get_logger, url_logging, response_error_parser

from .endpoints.hello import Hello
from .endpoints.package_info import PackageInfo
from .endpoints.pkgset_packages import PackagesetPackages

ns = Namespace('site', description="web site API")

from .parsers import site_hello_args, package_info_args, pkgset_packages_args
from .serializers import package_info_model, pkgset_packages_model

logger = get_logger(__name__)


@ns.route('/hello',
    doc={
        'description': "test endpoint",
        'responses': {
            200: 'Success',
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routeHello(Resource):
    @ns.expect(site_hello_args)
    # @ns.marshal_with(package_info_model)
    def get(self):
        args = site_hello_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = Hello(g.connection, **args)
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
    # @ns.marshal_with(package_info_model)
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


@ns.route('/repository_packages',
    doc={
        'description': ("Get list of packageset files in accordance "
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
