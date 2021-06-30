from collections import defaultdict, namedtuple

from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level as ll
from utils import tuplelist_to_dict, remove_duplicate, join_tuples

from api.misc import lut
from database.package_sql import packagesql
from libs.package_dependencies import PackageDependencies
from libs.exceptions import SqlRequestError

logger = get_logger(__name__)


class BuildDependencySet:
    def __init__(self, connection, packages, branch, archs, debug_):
        self.conn = connection
        self.sql = packagesql
        self.DEBUG = debug_
        self.status = False
        self.packages = tuple(packages)
        self.branch = branch
        self.archs = archs
        self.result = []
        self.error = None
        # add 'noarch' to archs list
        if 'noarch' not in self.archs:
            self.archs += ['noarch']

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
        self.status = False
        self._log_error(severity)

    def _store_error(self, message, severity, http_code):
        self.error = message, http_code
        self.status = False
        self._log_error(severity)

    def build_dependency_set(self):
        self.conn.request_line = self.sql.get_pkg_hshs.format(
            pkgs=self.packages, branch=self.branch
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return
        if not response:
            self._store_error(
                {"message": f"Packages {list(self.packages)} not found in package set '{self.branch}'"},
                ll.INFO, 404
            )
            return

        hshs = join_tuples(response)

        pkg_deps = PackageDependencies(self.conn, hshs, self.branch, self.archs, self.DEBUG)

        try:
            self.result = pkg_deps.build_result()
        except SqlRequestError as e:
            self._store_error(
                {
                    'message': f"Error occured in ConflictFilter",
                    'error': e.dErrorArguments
                },
                ll.ERROR,
                500
            )
            return

        self.status = True
        return


class PackageBuildDependencySet:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = packagesql
        self.args = kwargs
        self.validation_results = None

    def check_params(self):
        logger.debug(f"args : {self.args}")
        self.validation_results = []

        for pkg in self.args['packages']:
            if pkg == '':
                self.validation_results.append("package list should not contain empty values")
                break

        if self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

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
                'request_args' : self.args,
                'length': len(self.bds.result),
                'packages': self.bds.result
            }
            return res, 200
        else:
            return self.bds.error
