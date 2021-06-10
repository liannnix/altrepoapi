from flask_restx import fields, Model
from api.restplus import api

task_info_model = api.model('TaskInfoModel',
    {
        'task_id': fields.Integer(description='task id'),
        'subtask_id': fields.Integer(description='subtask id'),
        'subtask_contents': fields.Raw(description='subtask contents')
    }
)
