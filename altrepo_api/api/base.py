# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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

from typing import Any, Callable, NamedTuple, Optional, Protocol, Union
from flask_restx import abort

from altrepo_api.settings import namespace as settings
from altrepo_api.utils import response_error_parser, get_logger, logger_level

# type alias
WorkerResultWithHeaders = tuple[Any, int, dict[str, str]]
WorkerResultWithoutHeaders = tuple[Any, int]
WorkerResult = Union[WorkerResultWithHeaders, WorkerResultWithoutHeaders]


class ConnectionProto(Protocol):
    request_line: Union[str, tuple[str, Any]]

    def send_request(self, **query_kwargs) -> tuple[bool, Any]:
        ...

    def drop_connection(self) -> None:
        ...


class Response(NamedTuple):
    result: Any
    http_code: int
    headers: dict[str, str] = dict()


class APIWorker:
    """Base API endpoint worker class."""

    DEBUG = settings.SQL_DEBUG
    LL = logger_level()

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.status: bool = False
        self.error: tuple[Any, int]
        self.sql_status: bool = False
        self.conn: ConnectionProto
        self.validation_results: list[str] = []

    def _log_error(self, severity: int) -> None:
        if severity == self.LL.CRITICAL:
            self.logger.critical(self.error)
        elif severity == self.LL.ERROR:
            self.logger.error(self.error)
        elif severity == self.LL.WARNING:
            self.logger.warning(self.error)
        elif severity == self.LL.INFO:
            self.logger.info(self.error)
        else:
            self.logger.debug(self.error)

    def _build_sql_error_response(
        self, response: dict[str, Any], code: int
    ) -> tuple[Any, int]:
        """Add SQL request details from class to response dictionary if debug is enabled."""

        if self.DEBUG:
            response["module"] = self.__class__.__name__
            requestline = self.conn.request_line
            if isinstance(requestline, tuple):
                response["sql_request"] = [
                    x for x in requestline[0].split("\n") if len(x) > 0
                ]
            else:
                response["sql_request"] = [x for x in requestline.split("\n")]  # type: ignore
        return response, code

    def _store_sql_error(self, message: Any, severity: int, http_code: int) -> None:
        self.error = self._build_sql_error_response(message, http_code)
        self._log_error(severity)
        self.status = False

    def _store_error(self, message: Any, severity: int, http_code: int) -> None:
        self.error = message, http_code
        self._log_error(severity)
        self.status = False

    def send_sql_request(
        self, request_line: Any, http_code: int = 500, **kwargs
    ) -> Any:
        """Send SQL request and returns response. If request fails,
        saves SQL error to self.error object. Changes self.sql_status field."""

        self.conn.request_line = request_line
        self.sql_status, response = self.conn.send_request(**kwargs)
        if not self.sql_status:
            self._store_sql_error(response, self.LL.ERROR, http_code)
        return response

    def store_error(
        self,
        message: dict[str, Any],
        severity: int = LL.INFO,
        http_code: int = 404,
    ) -> tuple[Any, int]:
        """Build and returns APIWorker error object."""

        self._store_error(message, severity, http_code)
        return self.error

    def check_params(self) -> bool:
        return True

    def get(self) -> WorkerResult:
        return "OK", 200


def _abort_on_validation_error(
    worker: APIWorker, method: Callable[[], bool], args: Any
):
    """Call Flask abort() on APIWorker validation method call returned Flase."""

    if not method():
        abort(
            400,  # type: ignore
            message="Request parameters validation error",
            args=args,
            validation_message=worker.validation_results,
        )


def _abort_on_result_error(
    method: Callable[[], WorkerResult], ok_code: int
) -> Response:
    """Call Flask abort() if APIWorker run method call returned not 'ok_code'."""

    response = Response(*method())  # type: ignore
    if response.http_code != ok_code:
        abort(response.http_code, **response_error_parser(response.result))  # type: ignore
    return response


def run_worker(
    *,
    worker: APIWorker,
    run_method: Optional[Callable[[], WorkerResult]] = None,
    check_method: Optional[Callable[[], bool]] = None,
    args: Any = None,
    ok_code: int = 200,
) -> Response:
    """Calls APIWorker class's 'check_method' and 'run_method' and returns the result.

    Calls flask_restx abort() if check_method() returned False
    or if run_method() returned code not equal to 'ok_code'.
    Otherwise returns run_method() results wrapped in `Response` class.

    Default 'run_method' is worker.get().
    Default 'check_method' is worker.check_params()."""

    # run APIWorker validator method
    if check_method is None:
        check_method = worker.check_params
    _abort_on_validation_error(worker=worker, method=check_method, args=args)
    # run APIWorker run method
    if run_method is None:
        run_method = worker.get
    return _abort_on_result_error(method=run_method, ok_code=ok_code)


GET_RESPONSES_404 = {
    200: "Success",
    404: "Requested data not found in database",
}

GET_RESPONSES_400_404 = {
    200: "Success",
    400: "Request parameters validation error",
    404: "Requested data not found in database",
}

POST_RESPONSES_400_404 = {
    201: "Data loaded",
    400: "Request parameters validation error",
    404: "Requested data not found in database",
}
