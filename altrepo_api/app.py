# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from flask import Flask, redirect, g, request

from altrepo_api import read_config
from altrepo_api.utils import get_logger, CustomJSONEncoder

from altrepo_api.database.connection import Connection
from altrepo_api.api_v1 import blueprint as api_bp


app = Flask(__name__)
logger = get_logger(__name__)


@app.route("/")
def hello():
    return redirect("/api/", code=302)


@app.before_request
def init_db_connection():
    g.connection = Connection()
    g.url = request.url


@app.teardown_request
def drop_connection(exception):
    g.connection.drop_connection()  # type: ignore


@app.errorhandler  # type: ignore
def default_error_handler(e):
    message = "An unhandled exception occurred."
    logger.exception(message)

    if not read_config.settings.FLASK_DEBUG:
        return {"message": message}, 500


@app.after_request
def add_headers(response):
    """Add headers to all API responses here."""
    # response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def configure_app(flask_app):
    flask_app.config["SWAGGER_UI_DOC_EXPANSION"] = "list"
    flask_app.config["SWAGGER_UI_REQUEST_DURATION"] = True
    flask_app.config["RESTX_VALIDATE"] = True
    flask_app.config["ERROR_404_HELP"] = False
    flask_app.config["RESTX_MASK_SWAGGER"] = False
    flask_app.config["BUNDLE_ERRORS"] = True
    flask_app.config["RESTX_INCLUDE_ALL_MODELS"] = False
    flask_app.config["RESTX_JSON"] = {"cls": CustomJSONEncoder}


def initialize_app(flask_app):
    if not read_config.settings.ADMIN_PASSWORD:
        raise RuntimeError("API administration password should be specified")
    configure_app(flask_app)
    flask_app.register_blueprint(api_bp)


initialize_app(app)
