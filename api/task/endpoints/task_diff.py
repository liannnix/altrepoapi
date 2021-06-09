from flask_restplus import fields
from utils import get_logger

logger = get_logger(__name__)

class TaskDiff():
    description = (
        "task difference from previous task with details"
    )
    
    marshal_with = {
        # 'task_id': fields.Integer,
        # 'task_repo': fields.String,
        # 'task_pkgs': fields.Nested({
        #     'pkg_hash': fields.Integer,
        #     'pkg_name': fields.String
        # })
    }

    def __init__(self, connection, task_id) -> None:
        self.conn = connection
        self.task_id = task_id

    def get(self):
        if self.task_id == 123456:
            return {"message": f"task id {self.task_id} not found"}, 404
        self.conn.request_line = \
            """SELECT * FROM system.numbers LIMIT 5"""
        status, response = self.conn.send_request()
        if not status:
            return response, 500
        res = [_[0] for _ in response]
        return {
            'test': 'test',
            'task_id': self.task_id,
            'sql': res
        }
