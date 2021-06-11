from flask import  Flask, redirect, g, Blueprint, request
from flask_restx import Resource, fields

import utils
from database.connection import Connection

from api.restplus import api
from api.task.task import ns as task_ns

app = Flask(__name__)
logger = utils.get_logger(__name__)

version_fields = api.model('APIVersion',
    {
        'name': fields.String(attribute='title', description='API name'),
        'version': fields.String(description='API version'),
        'description': fields.String(description='API description')
    }
)

@api.route('/version/')
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

def configure_app(flask_app):
    flask_app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
    flask_app.config['SWAGGER_UI_REQUEST_DURATION'] = True
    flask_app.config['RESTX_VALIDATE'] = True
    flask_app.config['ERROR_404_HELP'] = False
    flask_app.config['RESTX_MASK_SWAGGER'] = False

def initialize_app(flask_app):
    configure_app(flask_app)
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    api.init_app(api_bp)
    api.add_namespace(task_ns)
    flask_app.register_blueprint(api_bp)

initialize_app(app)

if __name__ == '__main__':
    app.run()