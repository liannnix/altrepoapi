from sys import prefix
from flask import  Flask, request, g, Blueprint
from flask_restplus import Resource, Api, marshal_with, fields
# from flask_cors import CORS

import utils
from utils import func_time, json_serialize
from database.connection import Connection
from utils import namespace

app = Flask(__name__)
# CORS(app)

logger = utils.get_logger(__name__)

app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'

api_bp = Blueprint('api', __name__, url_prefix='/api')
api = Api(
    api_bp,
    version='1.0',
    title='altrepodb',
    description='altrepodb API',
    default='api',
    default_label='base functions'
)


class Greeter(Resource):
    def get(self):
        return {'message': 'Welcome to altrepo API!'}, 200

version_fields ={
    'version': fields.String,
    'description': fields.String
}
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


api.add_resource(Greeter, '/hello/')
api.add_resource(ApiVersion, '/version/')
api.add_resource(DBTest, '/database_test/')

app.register_blueprint(api_bp)

@app.before_request
def init_db_connection():
    g.connection = Connection()


@app.teardown_request
def drop_connection(exception):
    g.connection.drop_connection()


@app.errorhandler(404)
def page_404(error):
    return {'Error': error.description}

@api.errorhandler
def default_error_handler(e):
    message = 'An unhandled exception occurred.'
    logger.exception(message)

    if not namespace.FLASK_DEBUG:
        return {'message': message}, 500


# @api.errorhandler(NoResultFound)
# def database_not_found_error_handler(e):
#     """No results found in database"""
#     log.warning(traceback.format_exc())
#     return {'message': 'A database result was required but none was found.'}, 404


if __name__ == '__main__':
    app.run()