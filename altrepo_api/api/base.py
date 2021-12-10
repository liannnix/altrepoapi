# ALTRepo API
# Copyright (C) 2021  BaseALT Ltd

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from typing import Any, Tuple

from altrepo_api.settings import namespace as settings
from altrepo_api.utils import get_logger, logger_level
from altrepo_api.database.connection import Connection


class APIWorker:
    """Base API endpoint worker class."""

    DEBUG = settings.SQL_DEBUG

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.ll = logger_level
        self.status: bool = False
        self.error: Tuple[Any, int]
        self.conn: Connection
        self.validation_results: list = []

    def _log_error(self, severity: int) -> None:
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

    def _build_sql_error_response(self, response: dict, code: int) -> Tuple[Any, int]:
        """Add SQL request details from class to response dictionary if debug is enabled."""
        if self.DEBUG:
            response["module"] = self.__class__.__name__
            requestline = self.conn.request_line
            if isinstance(requestline, tuple):
                response["sql_request"] = [
                    _ for _ in requestline[0].split("\n") if len(_) > 0
                ]
            else:
                response["sql_request"] = [_ for _ in requestline.split("\n")]
        return response, code

    def _store_sql_error(self, message: Any, severity: int, http_code: int) -> None:
        self.error = self._build_sql_error_response(message, http_code)
        self._log_error(severity)
        self.status = False

    def _store_error(self, message: Any, severity: int, http_code: int) -> None:
        self.error = message, http_code
        self._log_error(severity)
        self.status = False

    def check_params(self) -> bool:
        return True

    def get(self) -> Any:
        return "OK", 200
