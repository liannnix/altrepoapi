from flask import  Flask, request, json, jsonify, g, make_response
from flask_restplus import Resource, Api
from flask_cors import CORS

import utils
from utils import func_time, json_serialize
from database.connection import Connection

app = Flask(__name__)
CORS(app)

logger = utils.get_logger(__name__)

@app.route('/')
class Greeter(Resource):
    def get(self):
        return {'message': 'Welcome to altrepo API'}, 200

@app.after_request
def after_request_func(data):
    response = make_response(data)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.before_request
def init_db_connection():
    g.connection = Connection()


@app.teardown_request
def drop_connection():
    g.connection.drop_connection()


@app.errorhandler(404)
def page_404(error):
    return {'Error': error.description}


if __name__ == '__main__':
    app.run()