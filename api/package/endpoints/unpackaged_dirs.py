from collections import namedtuple

from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level as ll

from api.misc import lut
from database.package_sql import packagesql

logger = get_logger(__name__)


class UnpackagedDirs:
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

        if self.args['packager'] == '':
            self.validation_results.append("packager nickname not specified")

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
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
        self.packager = self.args['packager']
        self.branch = self.args['branch']
        self.archs = self.args['archs']
        if self.archs:
            if 'noarch' not in self.archs:
                self.archs.append('noarch')
        else:
            self.archs = lut.default_archs
        self.archs = tuple(self.archs)
        
        self.conn.request_line = (
            self.sql.get_unpackaged_dirs,
            {
                'branch': self.branch,
                'email': '{}@%'.format(self.packager),
                'archs': self.archs
            }
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

        DirsInfo = namedtuple('DirsInfo', [
            'package', 'directory', 'version', 'release', 'epoch',
            'packager', 'email', 'archs'
        ])

        retval = [DirsInfo(*el)._asdict() for el in response]

        res = {
                'request_args' : self.args,
                'length': len(retval),
                'packages': retval
            }
        return res, 200
