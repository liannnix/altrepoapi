from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level as ll
from utils import datetime_to_iso, tuplelist_to_dict, convert_to_dict, join_tuples

from api.misc import lut
from database.site_sql import sitesql

logger = get_logger(__name__)


class Hello:
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
        pass
        return True

    def get(self):
        return "Hello there!", 200
