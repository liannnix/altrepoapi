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

        # if values['task']:
        #     g.connection.request_line = \
        #         "SELECT task_repo FROM Tasks WHERE task_id = {}".format(values['task'])

        #     status, response = g.connection.send_request()
        #     if status is False:
        #         return response

        #     pbranch = response[0][0]

        #     g.connection.request_line = (
        #         QM.build_dep_set_get_src_hsh_by_task, {'task': values['task']}
        #     )

        #     status, response = g.connection.send_request()
        #     if status is False:
        #         return response

        #     hshs = utils.join_tuples(response)
        # else:
        # pkg_ls = tuple(values['pkg_ls'].split(','))
        # pbranch = values['branch']

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

        pkg_deps = PackageDependencies(self.conn, self.branch, self.DEBUG)

        if self.archs:
            pkg_deps.static_archs += [
                arch for arch in self.archs
                if arch not in pkg_deps.static_archs
            ]

        try:
            dep_hsh_list = pkg_deps.get_package_dep_set(pkgs=hshs, first=True)
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

        try:
            result_dict = pkg_deps.make_result_dict(
                list(dep_hsh_list.keys()) +
                [hsh for val in dep_hsh_list.values() for hsh in val],
                dep_hsh_list
            )
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


        self.result = result_dict
        self.status = True


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
        pass
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
