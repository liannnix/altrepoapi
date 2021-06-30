from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level as ll

from api.misc import lut
from database.task_sql import tasksql
from api.package.endpoints.build_dependency_set import BuildDependencySet

logger = get_logger(__name__)


class TaskBuildDependencySet:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, id, **kwargs) -> None:
        self.conn = connection
        self.task_id = id
        self.sql = tasksql
        self.args = kwargs
        self.validation_results = None
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
            logger.error(build_sql_error_response(response, self, 500, self.DEBUG))
            return False

        if response[0][0] == 0:
            return False
        return True

    def check_params(self):
        logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['archs']:
            for arch in self.args['archs']:
                if arch not in lut.known_archs:
                    self.validation_results.append(f"unknown package arch : {arch}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        # arguments processing
        if self.args['archs'] is None:
            self.args['archs'] = ['x86_64']
        self.args['packages'] = []
        self.args['branch'] = None
        # get task source packages and branch
        # get task repo
        self.conn.request_line = self.sql.task_repo.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data found in database for task '{self.task_id}'"},
                ll.INFO, 404
            )
            return self.error

        self.args['branch'] = response[0][0]
        # get task source packages
        self.conn.request_line = self.sql.task_src_packages.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No packages found in database for task '{self.task_id}'"},
                ll.INFO, 404
            )
            return self.error
        self.args['packages'] = [pkg[0] for pkg in response]
        # init BuildDependency class with args
        self.bds = BuildDependencySet(
            self.conn,
            self.args['packages'],
            self.args['branch'],
            self.args['archs'],
            self.DEBUG
        )
        # build result
        self.bds.build_dependency_set()
        # format result
        if self.bds.status:
            # result processing
            res = {
                'id': self.task_id,
                'request_args' : self.args,
                'length': len(self.bds.result),
                'packages': self.bds.result
            }
            return res, 200
        else:
            return self.bds.error
