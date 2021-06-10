from flask import Blueprint, g
from flask_restx import Resource, abort
from api.restplus import api
from utils import get_logger, url_logging

from api.task.parsers import task_info_args
from  api.task.serializers import task_info_model
from api.task.endpoints.task_diff import TaskDiff
from api.task.endpoints.task_info import TaskInfo

logger = get_logger(__name__)

task_bp = Blueprint('task', __name__)

ns = api.namespace('task', description='Test task API')


@ns.route('/task_info/<int:id>')
@ns.doc(
    params={'id': 'task ID'},
    responses={
        400: 'Request parameters validation failed',
        404: 'Task ID not found in database'
    },
    description="get information for task by ID"
)
class routeTaskInfo(Resource):
    @ns.expect(task_info_args)
    @ns.marshal_with(task_info_model, as_list=True)
    def get(self, id):
        args = task_info_args.parse_args()
        url_logging(logger, g.url)
        task_diff = TaskInfo(g.connection, id, args['try'], args['iteration'])
        if not task_diff.check_task_id():
            # abort(404, message='Task ID not found in database', task_id=id)
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        if not task_diff.check_params():
            abort(400, message=f"Request parameters validation failed", args=args)
        result, code =  task_diff.get()
        if code != 200:
            abort(code, message="Error occured during request handeling", details=result)
        return result, code
