import os
import pytest

from flask import Flask
from flask import Blueprint
from flask_restx import Api, Resource

os.environ["ALTREPO_API_CONFIG"] = "./tests/api.conf"

from altrepo_api import read_config  # noqa
from altrepo_api.utils import CustomJSONEncoder, get_logger
from altrepo_api.api.auth.decorators import auth_required

from tests.authorization.assets import slapdtest
from tests.authorization.test_api_authorization import (
    TEST_ROUTE_ADMIN_AUTH,
    TEST_ROUTE_LDAP_USER_AUTH,
    TEST_ROUTE_LDAP_ADMIN_AUTH,
)


def make_app():
    """Builds an instance of API with authorization test routes."""

    authorizations = {
        "BasicAuth": {"type": "basic", "in": "header", "name": "Authorization"}
    }
    bp = Blueprint("api", __name__, url_prefix="/api")
    api = Api(
        bp,
        version="0.0.0",
        title="test API",
        description="test API",
        default="api",
        default_label="basic functions",
        authorizations=authorizations,
    )

    @api.route(TEST_ROUTE_ADMIN_AUTH)
    class Auth(Resource):
        @api.doc(description="API authorization check")
        @api.doc(security="BasicAuth")
        @auth_required(admin_only=True)
        def get(self):
            return {"message": "authorized"}, 200

    @api.route(TEST_ROUTE_LDAP_ADMIN_AUTH)
    class AuthLDAPAdmin(Resource):
        @api.doc(description="API LDAP authorization check")
        @api.doc(security="BasicAuth")
        @auth_required(ldap_group=read_config.settings.AG.API_ADMIN, admin_only=True)
        def get(self):
            return {"message": "authorized"}, 200

    @api.route(TEST_ROUTE_LDAP_USER_AUTH)
    class AuthLDAPUser(Resource):
        @api.doc(description="API LDAP authorization check")
        @api.doc(security="BasicAuth")
        @auth_required(ldap_group=read_config.settings.AG.API_USER)
        def get(self):
            return {"message": "authorized"}, 200

    app = Flask("app")
    logger = get_logger("app")

    @app.errorhandler  # type: ignore
    def default_error_handler(e):
        message = "An unhandled exception occurred."
        logger.exception(message)

        return {"message": message}, 500

    app.config["BUNDLE_ERRORS"] = True
    app.config["RESTX_JSON"] = {"cls": CustomJSONEncoder}

    app.register_blueprint(bp)

    return app


test_app = make_app()


@pytest.fixture
def app():
    return test_app


@pytest.fixture
def slapd():
    here = os.path.dirname(__file__)
    server = slapdtest.SlapdObject()
    server.suffix = "o=test"
    server.openldap_schema_files = [  # type: ignore
        "core.ldif",
        "cosine.ldif",
        "inetorgperson.ldif",
        "nis.ldif",
    ]
    server.start()
    with open(os.path.join(here, "assets/test.ldif")) as fp:
        ldif = fp.read()
    server.slapadd(ldif)

    yield server

    server.stop()
