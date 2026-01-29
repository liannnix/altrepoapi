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
from typing import Any, Union
from clickhouse_driver import Client, errors
from clickhouse_driver.defines import DBMS_MIN_REVISION_WITH_INTERSERVER_SECRET_V2

from altrepo_api.settings import namespace as settings
from altrepo_api.utils import get_logger, exception_to_logger, json_str_error

logger = get_logger(__name__)

QueryT = Union[str, tuple[str, Any]]


class Connection:
    """Handles connection to ClickHouse database."""

    def __init__(self):
        self.query: QueryT = ""
        self.connection_status = False

        self.client = Client(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASS,
            client_revision=DBMS_MIN_REVISION_WITH_INTERSERVER_SECRET_V2,
        )

        if not self._connect():
            raise RuntimeError("Failed to connect to database")

    def _connect(self) -> bool:
        if self.connection_status:
            try:
                self.client.execute("SELECT 1")
                logger.debug("Database connection is alive.")
                return True
            except errors.Error as error:
                logger.debug(f"Database connection failed: {error}")
                self.connection_status = False

        try:
            self.client.connection.connect()
            logger.debug("Database connection established.")
        except errors.Error as error:
            logger.error(exception_to_logger(error))
            return False

        self.connection_status = True
        return True

    def _debug_sql_query(self) -> None:
        if not settings.SQL_DEBUG:
            return
        if isinstance(self.query, tuple):
            # SQL query has params
            try:
                # XXX: works only for clickhouse-driver >= 0.2.3
                query = self.client.substitute_params(
                    self.query[0],
                    self.query[1],
                    self.client.connection.context,
                )
            except ValueError:
                query = self.query[0]
        else:
            query = self.query

        logger.debug(f"SQL request:\n{query}")

    def _disconnect(self) -> None:
        self.client.disconnect()
        self.connection_status = False

    def drop_connection(self) -> None:
        self._disconnect()
        logger.debug("Connection closed.")

    def send_request(self, query: QueryT, **query_kwargs: Any) -> tuple[bool, Any]:
        self.query = query
        response_status = False

        for try_ in range(settings.TRY_CONNECTION_NUMBER):
            logger.debug(f"Attempt to connect to the database #{try_ + 1}")

            if self._connect():
                break

            sleep(settings.TRY_TIMEOUT)

        if not self.connection_status:
            return response_status, json_str_error("Database connection error.")

        try:
            self._debug_sql_query()
            if isinstance(query, tuple):
                response = self.client.execute(query[0], query[1], **query_kwargs)
            else:
                response = self.client.execute(query, **query_kwargs)
            response_status = True
            logger.debug(
                f"SQL request elapsed {self.client.last_query.elapsed:.3f} seconds"  # type: ignore
            )
        except errors.Error as error:
            logger.error(exception_to_logger(error))
            response = json_str_error("Error in SQL query!")

        return response_status, response
