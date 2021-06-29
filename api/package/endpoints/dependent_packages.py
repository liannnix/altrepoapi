from collections import namedtuple

from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level as ll
from utils import tuplelist_to_dict

from api.misc import lut
from database.package_sql import packagesql

logger = get_logger(__name__)


class DependentPackages:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = packagesql
        self.args = kwargs
        self.validation_results = None

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

        if self.args['name'] == '':
            self.validation_results.append("file name not specified")

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.package = self.args['name']
        self.branch = self.args['branch']
        
        self.conn.request_line = self.sql.get_dependent_packages.format(
            package=self.package, branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data found in database for given parameters",
                "args": self.args},
                ll.INFO,
                404
            )
            return self.error

        PkgInfo = namedtuple('PkgInfo', [
            'name', 'version', 'release', 'epoch', 'serial',
            'sourcerpm', 'branch', 'archs'
        ])

        retval = [PkgInfo(*el)._asdict() for el in response]

        res = {
                'request_args' : self.args,
                'length': len(retval),
                'packages': retval
            }
        return res, 200
