from flask_restplus import reqparse

task_info_args = reqparse.RequestParser()
task_info_args.add_argument('try', type=int, required=False, help='task try', location='args')
task_info_args.add_argument('iteration', type=int, required=False, help='task iteration', location='args')