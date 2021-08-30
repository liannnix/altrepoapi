from flask import g
from flask_restx import Resource, abort, Namespace

from api.bug.endpoints.bugzilla_info import Bugzilla
from utils import get_logger, url_logging, response_error_parser
from api.bug.parsers import package_bugzilla_args, maintainer_bugzilla_args
from api.bug.serializers import bugzilla_info_model

ns = Namespace("bug", description="bug information API")
logger = get_logger(__name__)


@ns.route(
    "/bugzilla_by_package",
    doc={
        "description": "Get information from bugzilla by the name source package",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeBugzillaByPackage(Resource):
    @ns.expect(package_bugzilla_args)
    @ns.marshal_list_with(bugzilla_info_model)
    def get(self):
        args = package_bugzilla_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = Bugzilla(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get_bug_by_package()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/bugzilla_by_maintainer",
    doc={
        "description": "Get information from bugzilla by the maintainer nickname",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeBugzillaByMaintainer(Resource):
    @ns.expect(maintainer_bugzilla_args)
    @ns.marshal_list_with(bugzilla_info_model)
    def get(self):
        args = maintainer_bugzilla_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = Bugzilla(g.connection, **args)
        if not wrk.check_params_maintainer():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get_bug_by_maintainer()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code