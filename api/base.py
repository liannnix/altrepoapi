from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level

class APIWorker:
    DEBUG = settings.SQL_DEBUG

    def __init__(self):
        self.logger = get_logger(__name__)
        self.ll = logger_level
        # self.conn = connection
        # self.args = kwargs
        # self.sql = sql
        self.status = False
        self.error = None
        self.validation_results = None

    def _log_error(self, severity):
        if severity == self.ll.CRITICAL:
            self.logger.critical(self.error)
        elif severity == self.ll.ERROR:
            self.logger.error(self.error)
        elif severity == self.ll.WARNING:
            self.logger.warning(self.error)
        elif severity == self.ll.INFO:
            self.logger.info(self.error)
        else:
            self.logger.debug(self.error)

    def _store_sql_error(self, message, severity, http_code):
        self.error = build_sql_error_response(message, self, http_code, self.DEBUG)
        self._log_error(severity)

    def _store_error(self, message, severity, http_code):
        self.error = message, http_code
        self._log_error(severity)

    def check_params(self):
        return True

    def get(self):
        return 'OK', 200
