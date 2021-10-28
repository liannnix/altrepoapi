from flask import Flask, redirect, g, request

from utils import get_logger
from settings import namespace as settings

from database.connection import Connection
from api import blueprint as api_bp

app = Flask(__name__)
logger = get_logger(__name__)

@app.route("/")
def hello():
    return redirect("api", code=302)


@app.before_request
def init_db_connection():
    g.connection = Connection()
    g.url = request.url


@app.teardown_request
def drop_connection(exception):
    g.connection.drop_connection()


@app.errorhandler
def default_error_handler(e):
    message = "An unhandled exception occurred."
    logger.exception(message)

    if not settings.FLASK_DEBUG:
        return {"message": message}, 500


def configure_app(flask_app):
    flask_app.config["SWAGGER_UI_DOC_EXPANSION"] = "list"
    flask_app.config["SWAGGER_UI_REQUEST_DURATION"] = True
    flask_app.config["RESTX_VALIDATE"] = True
    flask_app.config["ERROR_404_HELP"] = False
    flask_app.config["RESTX_MASK_SWAGGER"] = False
    flask_app.config["BUNDLE_ERRORS"] = True


def initialize_app(flask_app):
    if not settings.ADMIN_PASSWORD:
        raise RuntimeError("API administration password should be specified")
    configure_app(flask_app)
    flask_app.register_blueprint(api_bp)


initialize_app(app)

if __name__ == "__main__":
    app.run()
