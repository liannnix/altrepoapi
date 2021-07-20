from flask import g
from flask_restx import Resource, abort, Namespace

from utils import get_logger, url_logging, response_error_parser

from .endpoints.pkgset_compare import PackagesetCompare
from .endpoints.pkgset_packages import PackagesetPackages

ns = Namespace('packageset', description="Packageset information API")

from .parsers import pkgset_compare_args, pkgset_packages_args
from .serializers import pkgset_compare_model, pkgset_packages_model

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


@ns.route('/compare_packagesets',
    doc={
        'description': "Get difference list of packages from two package sets",
        'responses': {
            400: 'Request parameters validation error',
            404: 'Package not found in database'
        }
    }
)
class routePackagesetCompare(Resource):
    @ns.expect(pkgset_compare_args)
    @ns.marshal_with(pkgset_compare_model)
    def get(self):
        args = pkgset_compare_args.parse_args(strict=True)
        url_logging(logger, g.url)
        pkg= PackagesetCompare(g.connection, **args)
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
