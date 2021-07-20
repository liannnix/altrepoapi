from collections import namedtuple

from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level as ll

from api.misc import lut
from database.site_sql import sitesql

logger = get_logger(__name__)


class PackagesetPackages:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = sitesql
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

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['package_type'] not in ('source', 'binary', 'all'):
            self.validation_results.append(
                f"package type should be one of 'source', 'binary' or 'all' not '{self.args['package_type']}'"
            )

        if self.args['group']:
            if self.args['group'] not in lut.pkg_groups:
                self.validation_results.append(f"unknown package category : {self.args['group']}")
                self.validation_results.append(f"allowed package categories : {lut.pkg_groups}")

        if self.args['buildtime'] and self.args['buildtime'] < 0:
            self.validation_results.append(f"package build time should be integer UNIX time representation")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.pkg_type = self.args['package_type']
        self.branch = self.args['branch']
        self.group = self.args['group']
        self.buildtime = self.args['buildtime']

        if self.group is not None:
            self.group = f"AND pkg_group_ like '{self.group}%'"
        else:
            self.group = ''

        pkg_type_to_sql = {
            'source': (1,),
            'binary': (0,),
            'all': (1, 0)
        }
        sourcef = pkg_type_to_sql[self.pkg_type]

        self.conn.request_line = self.sql.get_repo_packages.format(
            buildtime=self.buildtime,
            branch=self.branch,
            group=self.group,
            src=sourcef
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
        
        
        PkgMeta = namedtuple('PkgMeta', [
            'hash', 'name', 'version', 'release', 'buildtime', 'summary', 'maintainer',
            'category', 'changelog'
        ])

        retval = [PkgMeta(*el)._asdict() for el in response]

        res = {
                'request_args' : self.args,
                'length': len(retval),
                'packages': retval
            }
        return res, 200
