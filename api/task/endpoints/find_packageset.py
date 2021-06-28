from collections import namedtuple

from settings import namespace as settings
from utils import get_logger, build_sql_error_response, join_tuples, logger_level as ll

from api.misc import lut
from database.task_sql import tasksql

logger = get_logger(__name__)

class FindPackageset:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, id, **kwargs) -> None:
        self.conn = connection
        self.sql = tasksql
        self.task_id = id
        self.args = kwargs
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

    def check_params(self):
        logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branches']:
            for br in self.args['branches']:
                if br not in lut.known_branches:
                    self.validation_results.append(f"unknown package set name : {br}")
                    self.validation_results.append(f"allowed package set names are : {lut.known_branches}")
                    break

        if self.validation_results != []:
            return False
        else:
            return True

    def check_task_id(self):
        self.conn.request_line = self.sql.check_task.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.INFO)
            return False

        if response[0][0] == 0:
            return False
        return True

    def get(self):
        self.conn.request_line = self.sql.task_src_packages.format(id=self.task_id)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {"message": f"No source packages found in database for task {self.task_id}"},
                ll.INFO,
                404
            )
            return self.error

        packages = join_tuples(response)

        if self.args['branches']:
            branchs_cond =  f"AND pkgset_name IN {tuple(self.args['branches'])}"
        else:
            branchs_cond = ''

        self.conn.request_line = (
            self.sql.get_branch_with_pkgs.format(branchs=branchs_cond),
            {'pkgs': packages}
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {"message": f"No results found in last package sets for given parameters",
                "args": self.args},
                ll.INFO,
                404
            )
            return self.error

        PkgsetInfo = namedtuple('PkgsetInfo', [
            'branch', 'sourcepkgname', 'pkgset_datetime', 'packages', 'version',
            'release', 'disttag', 'packager_email', 'buildtime', 'archs'
        ])

        res = [PkgsetInfo(*el)._asdict() for el in response]

        res = {
            'id': self.task_id,
            'request_args': self.args,
            'task_packages': list(packages),
            'length': len(res),
            'packages': res
        }

        return res, 200
