from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level as ll
from utils import datetime_to_iso, tuplelist_to_dict, convert_to_dict, join_tuples

from api.misc import lut
from database.package_sql import packagesql

logger = get_logger(__name__)

class FindPackageset:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = packagesql
        self.args = kwargs
        self.packages = tuple(self.args['packages'])
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

    def get(self):
        for pkg in self.packages:
            if pkg == '':
                self._store_error(
                    {"message": f"package list from argument should not contain empty values",
                    "packages": self.packages},
                    ll.INFO,
                    400
                )
                return self.error

        self.conn.request_line = (
            self.sql.get_branch_with_pkgs,
            {'pkgs': self.packages}
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {"message": f"No results found in last packages for given parameters",
                "args": self.args},
                ll.INFO,
                404
            )
            return self.error

        param_ls = [
            'branch', 'sourcepkgname', 'pkgset_datetime', 'packages', 'version',
            'release', 'disttag', 'packager_email', 'buildtime', 'archs'
        ]

        res = [_ for _ in convert_to_dict(param_ls, response).values()]

        res = {
            'request_args': self.args,
            'length': len(res),
            'packages': res
        }

        return res, 200
