from utils import get_logger, build_sql_error_response
from utils import tuplelist_to_dict, join_tuples, logger_level as ll, convert_to_dict
from database.package_sql import packagesql
from settings import namespace as settings
from api.misc import lut
from libs.dependency_sorting import SortList

logger = get_logger(__name__)


class MisconflictPackages:
    def __init__(self, connection, packages, branch, archs, debug_):
        self.conn = connection
        self.sql = packagesql
        self.DEBUG = debug_
        self.status = False
        self.packages = packages
        self.branch = branch
        self.arch = archs
        self.result = {}

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

    def build_dependencies(self):
        # do all kind of black magic here

        # magic ends here
        self.status = True


class PackageMisconflictPackages:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = packagesql
        self.args = kwargs
        self.validation_results = None

    def check_params(self):
        logger.debug(f"args : {self.args}")
        self.validation_results = []
        if self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['arch']:
            for arch in self.args['arch']:
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
        self.mp = MisconflictPackages(
            self.conn,
            self.args['package'],
            self.args['branch'].lower(),
            self.args['arch'],
            self.DEBUG)
        
        # build result
        self.mp.build_dependencies()

        # format result
        if self.mp.status:
            # result processing
            res = {
                'request_args' : self.args,
                'conflicts': [_ for _ in self.mp.result.values()]
            }
            res['length'] = len(res['dependencies'])
            return res, 200
        else:
            return self.mp.error
