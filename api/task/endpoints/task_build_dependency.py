from utils import get_logger, build_sql_error_response, logger_level as ll
from database.task_sql import tasksql
from api.package.endpoints.pkg_build_dependency import BuildDependency
from api.misc import lut
from settings import namespace as settings

logger = get_logger(__name__)


class TaskBuildDependency:
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

        if self.args['arch']:
            for arch in self.args['arch']:
                if arch not in lut.known_archs:
                    self.validation_results.append(f"unknown package arch : {arch}")

        if self.args['depth'] < 1 or self.args['depth'] > settings.DEPENDENCY_MAX_DEPTH:
            self.validation_results.append(
                f"dependency depth should be in range (1...{settings.DEPENDENCY_MAX_DEPTH})"
            )

        if self.args['dptype'] not in ('source', 'binary', 'both'):
            self.validation_results.append(
                f"dependency type should be one of 'source', 'binary' or 'both' not '{self.args['dptype']}'"
            )

        if None not in (self.args['filter_by_source'], self.args['filter_by_package']):
            self.validation_results.append(
                f"Parameters 'filter_by_src' and 'filter_by_package' can't be used together"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        # arguments processing
        self.args['package'] = []
        self.args['branch'] = None
        # get task source packages and branch
        # get task repo
        self.conn.request_line = self.sql.task_repo.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_sql_error(
                {"message": f"No data found in database for task '{self.task_id}'"},
                ll.INFO, 404
            )
            return self.error

        self.args['branch'] = response[0][0]
        # get task source packages
        self.conn.request_line = self.sql.build_task_src_packages.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_sql_error(
                {"message": f"No source packages found for task '{self.task_id}'"},
                ll.INFO, 404
            )
            return self.error
        self.args['package'] = list({pkg[0] for pkg in response})
        print(f"DBG: args : {self.args}")
        # init BuildDependency class with args
        self.bd = BuildDependency(
            self.conn,
            self.args['package'],
            self.args['branch'],
            self.args['arch'],
            self.args['leaf'],
            self.args['depth'],
            self.args['dptype'],
            self.args['filter_by_package'],
            self.args['filter_by_source'],
            self.args['finite_package'],
            self.DEBUG)
        
        # build result
        self.bd.build_dependencies()

        # format result
        if self.bd.status:
            # result processing
            res = {
                'id': self.task_id,
                'request_args' : self.args,
                'dependencies': [_ for _ in self.bd.result.values()]
            }
            res['length'] = len(res['dependencies'])
            return res, 200
        else:
            return self.bd.error
