from utils import get_logger, build_sql_error_response
from utils import datetime_to_iso, mmhash, logger_level as ll
from database.package_sql import packagesql
from settings import namespace as settings
from api.misc import lut
logger = get_logger(__name__)


class BuildDependency:
    def __init__(
        self, connection, pkgname, branch, arch, leaf, depth,
        dptype, filter, filtersrc, finitepkg, debug_
    ):
        self.conn = connection
        self.sql = packagesql
        self.DEBUG = debug_
        self.status = False
        self.input_packages = pkgname
        self.branch = branch
        self.arch = arch
        self.leaf = leaf
        self.depth = depth
        self.dptype = dptype
        self.reqfilter = filter
        self.reqfiltersrc = filtersrc
        self.finitepkg = finitepkg
        self.result = {}

    def store_sql_error(self, message, severity, http_code):
        self.error = build_sql_error_response(message, self, http_code, self.DEBUG)
        self.status = False
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

    def build_dependencies(self):
        # do all kind of black magic here
        
        self.status = True
        return self.result


class PackageBuildDependency:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = packagesql
        self.args = kwargs
        self.validation_results = []

    def check_params(self):
        if self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            return False

        for arch in self.args['arch']:
            if arch not in lut.known_archs:
                self.validation_results.append(f"unknown package arch : {arch}")
                return False

        if self.args['depth'] < 1 or self.args['depth'] > settings.DEPENDENCY_MAX_DEPTH:
            self.validation_results.append(f"dependency depth should be in range (1...{settings.DEPENDENCY_MAX_DEPTH})")
            return False

        return True

    def get(self):
        # arguments processing
        print(f"DBG: args : {self.args}")
        pass
        # init BuildDependency class with args
        self.bd = BuildDependency(
            self.conn,
            None,
            self.args['branch'],
            self.args['arch'],
            None,
            None,
            None,
            None,
            None,
            None,
            self.DEBUG)
        
        # build result
        res = self.bd.build_dependencies()

        # format result
        if self.bd.status:
            # result processing
            # return res, 200
            return self.args, 200
        else:
            return self.bd.error
