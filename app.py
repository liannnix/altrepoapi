from flask import  Flask, redirect, g, Blueprint, request
from flask_restx import Resource, fields

from utils import get_logger
from settings import namespace as settings

from database.connection import Connection
from api import api

app = Flask(__name__)
logger = get_logger(__name__)

version_fields = api.model('APIVersion',
    {
        'name': fields.String(attribute='title', description='API name'),
        'version': fields.String(description='API version'),
        'description': fields.String(description='API description')
    }
)

@api.route('/version')
class ApiVersion(Resource):
    @api.doc('get API information')
    @api.marshal_with(version_fields)
    def get(self):
        return api, 200

@app.route('/')
def hello():
    return redirect("api", code=302)

@app.before_request
def init_db_connection():
    g.connection = Connection()
    g.url = request.url

@app.teardown_request
def drop_connection(exception):
    g.connection.drop_connection()

@api.errorhandler
def default_error_handler(e):
    message = 'An unhandled exception occurred.'
    logger.exception(message)

    if not settings.FLASK_DEBUG:
        return {'message': message}, 500

# @api.errorhandler(NoResultFound)
# def database_not_found_error_handler(e):
#     """No results found in database"""
#     log.warning(traceback.format_exc())
#     return {'message': 'A database result was required but none was found.'}, 404

def configure_app(flask_app):
    flask_app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
    flask_app.config['SWAGGER_UI_REQUEST_DURATION'] = True
    flask_app.config['RESTX_VALIDATE'] = True
    flask_app.config['ERROR_404_HELP'] = False
    flask_app.config['RESTX_MASK_SWAGGER'] = False
    flask_app.config['BUNDLE_ERRORS'] = True

def initialize_app(flask_app):
    configure_app(flask_app)
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    api.init_app(api_bp)
    flask_app.register_blueprint(api_bp)

initialize_app(app)

if __name__ == '__main__':
    app.run()
