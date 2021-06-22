from utils import get_logger, build_sql_error_response
from utils import datetime_to_iso, mmhash, logger_level as ll
from database.package_sql import packagesql
from settings import namespace

logger = get_logger(__name__)


class PackageInfo:
    DEBUG = namespace.SQL_DEBUG

    def __init__(self, connection, pkg, hash) -> None:
        self.conn = connection
        self.pkg = pkg
        self.pkg_hash = hash
        self.sql = packagesql
        # self.task = Task(self.conn, self.task_id, self.task_try, self.task_iter, self.DEBUG)

    def check_package(self):
        # self.conn.request_line = self.sql.check_task.format(id=self.task_id)

        # status, response = self.conn.send_request()
        # if not status:
        #     logger.error(build_sql_error_response(response, self, 500, self.DEBUG))
        #     return False

        # if response[0][0] == 0:
        #     return False
        return True

    def check_params(self):
        # if self.task_try is not None and self.task_iter is not None:
        #     if self.task_try > 0 and self.task_iter > 0:
        #         return True
        #     else:
        #         return False
        # elif self.task_try is None and self.task_iter is None:
        #     return True
        # else:
        #     return False
        return True

    def get(self):
        pass
