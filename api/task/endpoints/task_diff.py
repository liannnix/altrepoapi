from utils import get_logger, build_sql_error_response

logger = get_logger(__name__)

class TaskDiff():
    description = (
        "task difference from previous task with details"
    )

    def __init__(self, connection, task_id) -> None:
        self.conn = connection
        self.task_id = task_id

    def get(self):
        return {
            'test': 'test',
            'task_id': self.task_id,
            'sql': {}
        }
