from flask import Blueprint, g, request
from flask_restplus import Resource, fields, marshal_with
from api.restplus import api
from api.task.endpoints.task_diff import TaskDiff
from utils import get_logger

logger = get_logger(__name__)

task_bp = Blueprint('task', __name__)

ns = api.namespace('task', description='Test task API')

@ns.route('/test')
class TaskTest(Resource):
    def get(self):
        conn = g.connection
        conn.request_line = \
            """SELECT * FROM system.numbers LIMIT 10"""
        status, response = conn.send_request()
        if not status:
            return response, 500
        res = [_[0] for _ in response]
        return {'message': 'test task API',
        'res': res}

@ns.route('/task_diff/<int:id>')
@api.doc(
    params={'id': 'task ID'},
    responses={
        200: TaskDiff.description,
        404: 'task ID not found in DB'
    }
)
class routeTaskDiff(Resource):
    def get(self, id):
        task_diff = TaskDiff(g.connection, id)
        return task_diff.get()
