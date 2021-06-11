from flask_restx import reqparse

task_info_args = reqparse.RequestParser()
task_info_args.add_argument(
    'try',
    type=int,
    required=False,
    help='task try',
    location='args'
)
task_info_args.add_argument(
    'iteration',
    type=int,
    required=False,
    help='task iteration',
    location='args'
)

task_repo_args = reqparse.RequestParser()
task_repo_args.add_argument(
    'include_task_packages',
    type=bool,
    required=False,
    default=False,
    help='include task packages in repository state',
    location='args'
)
