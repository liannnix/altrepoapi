from settings import namespace as settings

from api.base import APIWorker
from api.misc import lut
from database.task_sql import tasksql
from api.package.endpoints.pkg_build_dependency import BuildDependency


class TaskBuildDependency(APIWorker):
    def __init__(self, connection, id, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = tasksql
        self.task_id = id
        super().__init__()

    def check_task_id(self):
        self.conn.request_line = self.sql.check_task.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.INFO, 500)
            return False

        if response[0][0] == 0:
            return False
        return True

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
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
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_sql_error(
                {"message": f"No data found in database for task '{self.task_id}'"},
                self.ll.INFO, 404
            )
            return self.error

        self.args['branch'] = response[0][0]
        # get task source packages
        self.conn.request_line = self.sql.build_task_src_packages.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_sql_error(
                {"message": f"No source packages found for task '{self.task_id}'"},
                self.ll.INFO, 404
            )
            return self.error
        self.args['package'] = list({pkg[0] for pkg in response})
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
        )
        
        # build result
        self.bd.build_dependencies()

        # format result
        if self.bd.status:
            # result processing
            res = {
                'id': self.task_id,
                'request_args' : self.args,
                'length': len(self.bd.result),
                'dependencies': self.bd.result
            }
            return res, 200
        else:
            return self.bd.error
