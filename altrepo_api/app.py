# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

try:
    from orjson import dumps as orjson_dumps
    from orjson import OPT_SORT_KEYS, OPT_APPEND_NEWLINE, OPT_OMIT_MICROSECONDS
    import json

    def dumps(obj, **kwargs) -> str:
        option = (
            OPT_APPEND_NEWLINE
            | OPT_OMIT_MICROSECONDS
            | (OPT_SORT_KEYS if kwargs.get("sort_keys") else 0)
        )

        default = kwargs.get("default", None)

        # workaround to handle `cls` argument in tests
        # usually custom serializer class implements only `default` method
        cls = kwargs.get("cls", None)
        if cls:
            try:
                default = cls().default
            except AttributeError:
                pass

        return orjson_dumps(obj, default, option).decode("utf-8")

    json.dumps = dumps
except ImportError:
    pass

import time
from flask import Flask, redirect, g, request
from flask_cors import CORS

from altrepo_api import read_config
from altrepo_api.settings import namespace as settings
from altrepo_api.utils import get_logger, json_default

from altrepo_api.database.connection import Connection
from altrepo_api.api_v1 import blueprint as api_bp
from altrepo_api.manage_v1 import blueprint as manage_bp


app = Flask(__name__)
logger = get_logger(__name__)


@app.route("/")
def hello():
    return redirect("/api/", code=302)


@app.before_request
def init_db_connection():
    g.connection = Connection()
    g.url = request.url
    g.start = time.perf_counter()


@app.teardown_request
def drop_connection(exception):
    g.connection.drop_connection()
    elapsed = time.perf_counter() - g.start
    logger.info(f"Request to '{g.url}' elapsed {elapsed:.3f} seconds")


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


def configure_app(flask_app: Flask):
    flask_app.config["SWAGGER_UI_DOC_EXPANSION"] = "list"
    flask_app.config["SWAGGER_UI_REQUEST_DURATION"] = True
    flask_app.config["RESTX_ERROR_404_HELP"] = False
    flask_app.config["RESTX_MASK_SWAGGER"] = False
    flask_app.config["RESTX_VALIDATE"] = True
    flask_app.config["BUNDLE_ERRORS"] = True
    flask_app.config["RESTX_INCLUDE_ALL_MODELS"] = False
    # pass custom default JSON object conversion handler
    flask_app.config["RESTX_JSON"] = {"default": json_default}


def initialize_app(flask_app: Flask):
    if not read_config.settings.ADMIN_PASSWORD:
        raise RuntimeError("API administration password should be specified")
    configure_app(flask_app)
    flask_app.register_blueprint(api_bp)
    flask_app.register_blueprint(manage_bp)

    CORS(
        flask_app,
        resources={
            r"/*": {"origins": settings.CORS_ORIGINS, "supports_credentials": True}
        },
    )


initialize_app(app)
