from sys import prefix
from flask import  Flask, request, g, Blueprint
from flask_restplus import Resource, Api, marshal_with, fields

import utils
from utils import func_time, json_serialize
from database.connection import Connection
from settings import namespace

from api.restplus import api
from api.task.task import ns as task_test_ns

app = Flask(__name__)
logger = utils.get_logger(__name__)


@api.response(200, 'Just a hello from API')
class Greeter(Resource):
    def get(self):
        return {'message': 'Welcome to altrepo API!'}, 200


version_fields ={
    'version': fields.String,
    'description': fields.String
}
@api.response(200, 'API version and description')
class ApiVersion(Resource):
    @marshal_with(version_fields)
    def get(self):
        return api, 200


class DBTest(Resource):
    def get(self):
        conn = g.connection
        conn.request_line = \
            """SELECT * FROM system.numbers LIMIT 10"""
        status, response = conn.send_request()
        if not status:
            return response, 500
        return {'numbers': [_[0] for _ in response]}


@app.route('/')
def test():
    return "It's alive!"


@app.before_request
def init_db_connection():
    g.connection = Connection()

@app.teardown_request
def drop_connection(exception):
    g.connection.drop_connection()

def configure_app(flask_app):
    app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
    # flask_app.config['RESTPLUS_VALIDATE'] = True
    # flask_app.config['RESTPLUS_MASK_SWAGGER'] = False
    # flask_app.config['ERROR_404_HELP'] = False

def initialize_app(flask_app):
    configure_app(flask_app)
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    api.init_app(api_bp)
    api.add_namespace(task_test_ns)

    api.add_resource(Greeter, '/hello/')
    api.add_resource(ApiVersion, '/version/')
    api.add_resource(DBTest, '/database_test/')

    flask_app.register_blueprint(api_bp)

initialize_app(app)

if __name__ == '__main__':
    app.run()