from flask import Blueprint, g
from flask_restx import Resource, abort
from api.restplus import api
from utils import get_logger, url_logging

from api.task.parsers import task_info_args, task_repo_args, task_build_dep_args, task_misconflict_args
from api.task.serializers import task_info_model, task_repo_model, task_diff_model, task_build_dep_model, misconflict_pkgs_model
from api.task.endpoints.task_diff import TaskDiff
from api.task.endpoints.task_info import TaskInfo
from api.task.endpoints.task_repo import TaskRepo
from api.task.endpoints.misconflict_packages import TaskMisconflictPackages
from api.task.endpoints.task_build_dependency import TaskBuildDependency

logger = get_logger(__name__)

task_bp = Blueprint('task', __name__)

ns = api.namespace('task', description="Task's information API")


@ns.route('/task_info/<int:id>',
    doc={
        'params': {'id': 'task ID'},
        'description': "get information for task by ID",
        'responses': {
            200: 'Success',
            400: 'Request parameters validation error',
            404: 'Task ID not found in database'
        }
    }
)
class routeTaskInfo(Resource):
    @ns.expect(task_info_args)
    @ns.marshal_with(task_info_model, as_list=True)
    def get(self, id):
        args = task_info_args.parse_args(strict=True)
        url_logging(logger, g.url)
        task_info = TaskInfo(g.connection, id, args['try'], args['iteration'])
        if not task_info.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        if not task_info.check_params():
            abort(400, message=f"Request parameters validation failed", args=args)
        result, code =  task_info.get()
        if code != 200:
            abort(code, message="Error occured during request handeling", details=result)
        return result, code


@ns.route('/task_repo/<int:id>',
    doc={
        'params': {'id': 'task ID'},
        'description': "get repository state by ID",
        'responses': {
            400: 'Request parameters validation error',
            404: 'Task ID not found in database'
        }
    }
)
class routeTaskRepo(Resource):
    @ns.expect(task_repo_args)
    @ns.marshal_with(task_repo_model)
    def get(self, id):
        args = task_repo_args.parse_args(strict=True)
        url_logging(logger, g.url)
        task_repo = TaskRepo(g.connection, id, args['include_task_packages'])
        if not task_repo.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        task_repo.build_task_repo()
        if task_repo.status:
            return task_repo.get()
        else:
            return task_repo.error


@ns.route('/task_diff/<int:id>',
    doc={
        'params': {'id': 'task ID'},
        'description': "get task difference by ID",
        'responses': {
            404: 'Task ID not found in database'
        }
    }
)
class routeTaskDiff(Resource):
    @ns.marshal_with(task_diff_model)
    def get(self, id):
        url_logging(logger, g.url)
        task_diff = TaskDiff(g.connection, id)
        if not task_diff.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        result, code = task_diff.get()
        if code != 200:
            abort(code, message="Error occured during request handeling", details=result)
        return result, code


@ns.route('/build_dependency/<int:id>',
    doc={
        'params': {'id': 'task ID'},
        'description': "get packages build dependencies",
        'responses': {
            400: 'Request parameters validation error',
            404: 'Requested data not found in database'
        }
    }
)
class routePackageBuildDependency(Resource):
    @ns.expect(task_build_dep_args)
    @ns.marshal_with(task_build_dep_model)
    def get(self, id):
        args = task_build_dep_args.parse_args(strict=True)
        url_logging(logger, g.url)
        task_build_dep = TaskBuildDependency(g.connection, id, **args)
        if not task_build_dep.check_params():
            abort(400, 
            message=f"Request parameters validation error",
            args=args,
            validation_message=task_build_dep.validation_results)
        if not task_build_dep.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        result, code = task_build_dep.get()
        if code != 200:
            abort(code, message="Error occured during request handeling", details=result)
        return result, code

@ns.route('/misconflict/<int:id>',
    doc={
        'params': {'id': 'task ID'},
        'description': ("get packages with conflicting files in packages "
        "from task that do not have a conflict in dependencies"),
        'responses': {
            400: 'Request parameters validation error',
            404: 'Requested data not found in database'
        }
    }
)
class routeTaskMisconflictPackages(Resource):
    @ns.expect(task_misconflict_args)
    @ns.marshal_with(misconflict_pkgs_model)
    def get(self, id):
        args = task_misconflict_args.parse_args(strict=True)
        url_logging(logger, g.url)
        task_misconflict = TaskMisconflictPackages(g.connection, id, **args)
        if not task_misconflict.check_params():
            abort(400, 
            message=f"Request parameters validation error",
            args=args,
            validation_message=task_misconflict.validation_results)
        if not task_misconflict.check_task_id():
            abort(404, message=f"Task ID '{id}' not found in database", task_id=id)
        result, code = task_misconflict.get()
        if code != 200:
            abort(code, message="Error occured during request handeling", details=result)
        return result, code
