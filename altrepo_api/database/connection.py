# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

from time import sleep
from typing import Any, Iterable, Union
from clickhouse_driver import Client, errors, __version__ as chd_version
from clickhouse_driver.defines import DBMS_MIN_REVISION_WITH_INTERSERVER_SECRET_V2

from altrepo_api.settings import namespace as settings
from altrepo_api.utils import get_logger, exception_to_logger, json_str_error

logger = get_logger(__name__)


class DBConnection:
    """Handles connection to ClickHouse database."""

    def __init__(
        self,
        clickhouse_host: str,
        clickhouse_port: int,
        clickhouse_name: str,
        dbuser: str,
        dbpass: str,
        query: Union[str, tuple[str, Any]] = "",
    ):
        self.query = query
        self.query_kwargs = {}

        self.clickhouse_client = Client(
            host=clickhouse_host,
            port=clickhouse_port,
            database=clickhouse_name,
            user=dbuser,
            password=dbpass,
            client_revision=DBMS_MIN_REVISION_WITH_INTERSERVER_SECRET_V2,
        )

        try_conn = self._connection_test()
        if try_conn:
            raise RuntimeError(try_conn)

        self.connection_status = False

    def make_connection(self) -> bool:
        try:
            self.clickhouse_client.connection.connect()
        except Exception as error:
            logger.error(error)
            return False

        self.connection_status = True

        return True

    def _connection_test(self) -> Union[str, None]:
        logger.debug(
            f"Connecting to databse {settings.DATABASE_NAME}@{settings.DATABASE_HOST}"
            f":{settings.DATABASE_PORT}"
        )
        try:
            self.clickhouse_client.connection.connect()
        except Exception as error:
            if issubclass(error.__class__, errors.Error):
                logger.error(exception_to_logger(error))
                return "Error of database connection."
            else:
                raise error

        self.clickhouse_client.disconnect()
        return None

    def _debug_sql_query_printout(self) -> None:
        if not settings.SQL_DEBUG:
            return
        if isinstance(self.query, tuple):
            # SQL query has params
            if not isinstance(self.query[1], Iterable):
                if chd_version <= "0.2.2":
                    query = self.clickhouse_client.substitute_params(
                        self.query[0],
                        self.query[1],
                    )  # type: ignore
                else:
                    query = self.clickhouse_client.substitute_params(
                        self.query[0],
                        self.query[1],
                        self.clickhouse_client.connection.context,  # works only for clickhouse-driver >= 0.2.3
                    )
            else:
                query = self.query[0]
        else:
            query = self.query

        logger.debug(f"SQL request:\n{query}")

    def send_request(self) -> tuple[bool, Any]:
        response_status = False

        try:
            self._debug_sql_query_printout()
            if isinstance(self.query, tuple):
                response = self.clickhouse_client.execute(
                    self.query[0], self.query[1], **self.query_kwargs
                )
            else:
                response = self.clickhouse_client.execute(
                    self.query, **self.query_kwargs
                )
            response_status = True
            logger.debug(
                f"SQL request elapsed {self.clickhouse_client.last_query.elapsed:.3f} seconds"  # type: ignore
            )
        except Exception as error:
            if issubclass(error.__class__, errors.Error):
                logger.error(exception_to_logger(error))
                response = json_str_error("Error in SQL query!")
            else:
                raise error

        return response_status, response

    def disconnect(self) -> None:
        self.clickhouse_client.disconnect()
        self.connection_status = False


class Connection:
    """Database connection class supports retries if connection to dabase have been lost."""

    def __init__(self):
        self.request_line: Union[str, tuple[str, Any]] = ""
        self._db_connection = DBConnection(
            settings.DATABASE_HOST,
            settings.DATABASE_PORT,
            settings.DATABASE_NAME,
            settings.DATABASE_USER,
            settings.DATABASE_PASS,
        )

    def send_request(self, **query_kwargs) -> tuple[bool, Any]:
        status = self._db_connection.connection_status
        if not status:
            for try_ in range(settings.TRY_CONNECTION_NUMBER):
                logger.debug("Attempt to connect to the database #{}".format(try_ + 1))

                status = self._db_connection.make_connection()
                if status:
                    break

                sleep(settings.TRY_TIMEOUT)

        if status:
            self._db_connection.query_kwargs = query_kwargs
            self._db_connection.query = self.request_line  # type: ignore
            return self._db_connection.send_request()
        else:
            return False, json_str_error("Database connection error.")

    def drop_connection(self) -> None:
        if self._db_connection:
            self._db_connection.disconnect()
            logger.debug("Connection closed.")
