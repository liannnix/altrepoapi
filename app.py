from flask import  Flask, redirect, g, Blueprint
from flask_restplus import Resource, Api, marshal_with, fields

import utils
from utils import func_time, json_serialize
from database.connection import Connection
from settings import namespace

from api.restplus import api
from api.task.task import ns as task_test_ns

app = Flask(__name__)
logger = utils.get_logger(__name__)


@api.doc(description='just a hello from API')
class Greeter(Resource):
    def get(self):
        return {'message': 'Welcome to altrepodb API!'}, 200


version_fields = api.model('APIVersion',
    {
        'name': fields.String(attribute='title', description='API name'),
        'version': fields.String(description='API version'),
        'description': fields.String(description='API description')
    }
)

@api.doc(description='get API information')
class ApiVersion(Resource):
    @api.doc(model=version_fields)
    @marshal_with(version_fields, envelope='api')
    def get(self):
        return api, 200


@app.route('/')
def hello():
    return redirect("api", code=302)


@app.before_request
def init_db_connection():
    g.connection = Connection()

@app.teardown_request
def drop_connection(exception):
    g.connection.drop_connection()

def configure_app(flask_app):
    flask_app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
    flask_app.config['RESTPLUS_VALIDATE'] = True
    # flask_app.config['RESTPLUS_MASK_SWAGGER'] = False
    # flask_app.config['ERROR_404_HELP'] = False

def initialize_app(flask_app):
    configure_app(flask_app)
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    api.init_app(api_bp)
    api.add_namespace(task_test_ns)

    api.add_resource(Greeter, '/hello/')
    api.add_resource(ApiVersion, '/version/')

    flask_app.register_blueprint(api_bp)

initialize_app(app)

if __name__ == '__main__':
    app.run()