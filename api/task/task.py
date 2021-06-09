from flask import Blueprint, g
from flask_restplus import Resource, fields, marshal_with
from api.restplus import api
from utils import get_logger

from api.task.parsers import task_info_args
from  api.task.serializers import task_test_model
from api.task.endpoints.task_diff import TaskDiff
from api.task.endpoints.task_info import TaskInfo

logger = get_logger(__name__)

task_bp = Blueprint('task', __name__)

ns = api.namespace('task', description='Test task API')


@ns.route('/task_diff/<int:id>')
@api.doc(
    params={'id': 'task ID'},
    responses={
        404: 'Task ID not found in database'
    },
    description=TaskDiff.description
)
class routeTaskDiff(Resource):
    @api.doc(model=task_test_model)
    @marshal_with(task_test_model)
    def get(self, id):
        task_diff = TaskDiff(g.connection, id)
        return task_diff.get()


@ns.route('/task_info/<int:id>')
@api.doc(
    params={'id': 'task ID'},
    responses={
        404: 'Task ID not found in database'
    },
    description=TaskInfo.description
)
class routeTaskInfo(Resource):
    @api.expect(task_info_args)
    @api.doc(model=task_test_model)
    @marshal_with(task_test_model)
    def get(self, id):
        args = task_info_args.parse_args()
        task_diff = TaskInfo(g.connection, id, args['try'], args['iteration'])
        return task_diff.get()
