from flask_restplus import fields
from api.restplus import api

task_test_model = api.model('Task Test Model',
    {
        'task_id': fields.String(description='task id'),
        'sql': fields.Raw(description='sql list')
    }
)
