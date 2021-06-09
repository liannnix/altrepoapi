from utils import get_logger, build_sql_error_response

logger = get_logger(__name__)

class TaskInfo():
    description = (
        "task information"
    )

    def __init__(self, connection, id_, try_, iter_) -> None:
        self.conn = connection
        self.task_id = id_
        self.task_try = try_
        self.task_iter = iter_ 

    def get(self):
        print(f"DBG: {self.task_id}, {self.task_try}, {self.task_iter}")
        if self.task_id == 123456:
            return {"message": f"task id {self.task_id} not found"}, 404
        self.conn.request_line = \
            """SELECT * FROM system.numbers LIMIT 5"""
        status, response = self.conn.send_request()
        if not status:
            return build_sql_error_response(response, self, 500)
        res = [_[0] for _ in response]
        return {
            'test': 'test',
            'task_id': self.task_id,
            'sql': res
        }
