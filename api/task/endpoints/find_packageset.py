from settings import namespace as settings
from utils import get_logger, build_sql_error_response, join_tuples, logger_level as ll
from utils import convert_to_dict

from database.task_sql import tasksql

logger = get_logger(__name__)

class FindPackageset:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, id) -> None:
        self.conn = connection
        self.sql = tasksql
        self.task_id = id
        self.error = None

    def _log_error(self, severity):
        if severity == ll.CRITICAL:
            logger.critical(self.error)
        elif severity == ll.ERROR:
            logger.error(self.error)
        elif severity == ll.WARNING:
            logger.warning(self.error)
        elif severity == ll.INFO:
            logger.info(self.error)
        else:
            logger.debug(self.error)

    def _store_sql_error(self, message, severity, http_code):
        self.error = build_sql_error_response(message, self, http_code, self.DEBUG)
        self._log_error(severity)

    def _store_error(self, message, severity, http_code):
        self.error = message, http_code
        self._log_error(severity)

    def check_task_id(self):
        self.conn.request_line = self.sql.check_task.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.INFO)
            return False

        if response[0][0] == 0:
            return False
        return True

    def check_params(self, **kwargs):
        pass

    def get(self):
        self.conn.request_line = self.sql.task_src_packages.format(id=self.task_id)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {"message": f"No source packages found in dayabase for task {self.task_id}"},
                ll.INFO,
                404
            )
            return self.error

        packages = join_tuples(response)

        self.conn.request_line = (
            self.sql.get_branch_with_pkgs,
            {'pkgs': packages}
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {"message": f"No results found in last package sets for task {self.task_id}"},
                ll.INFO,
                404
            )
            return self.error

        param_ls = [
            'branch', 'sourcepkgname', 'pkgset_datetime', 'packages', 'version',
            'release', 'disttag', 'packager_email', 'buildtime', 'archs'
        ]

        res = [_ for _ in convert_to_dict(param_ls, response).values()]

        res = {
            'id': self.task_id,
            'task_packages': list(packages),
            'length': len(res),
            'packages': res
        }

        return res, 200
