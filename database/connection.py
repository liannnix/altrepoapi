# altrepodb API
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

import types
from time import sleep
from clickhouse_driver import Client, errors

from settings import namespace as settings
from utils import get_logger, exception_to_logger, json_str_error, print_statusbar

logger = get_logger(__name__)


class DBConnection:
    """Handles connection to ClickHouse database."""

    def __init__(
        self,
        clickhouse_host=None,
        clickhouse_name=None,
        dbuser=None,
        dbpass=None,
        db_query=None,
    ):

        self.db_query = db_query

        self.clickhouse_client = Client(
            host=clickhouse_host, database=clickhouse_name, user=dbuser, password=dbpass
        )

        try_conn = self._connection_test()
        if try_conn:
            raise RuntimeError(try_conn)

        self.connection_status = False

    def make_connection(self):
        try:
            self.clickhouse_client.connection.connect()
        except Exception as error:
            logger.error(error)
            return False

        self.connection_status = True

        return True

    def _connection_test(self):
        logger.debug(f"Connecting to databse {settings.DATABASE_NAME}@{settings.DATABASE_HOST}")
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

    def _debug_sql_query_printout(self):
        if not settings.SQL_DEBUG:
            return
        if isinstance(self.db_query, tuple):
            # SQL query has params
            if not isinstance(self.db_query[1], (list, tuple, types.GeneratorType)):
                query = self.clickhouse_client.substitute_params(self.db_query[0], self.db_query[1])
            else:
                query = self.db_query[0]
        else:
            query = self.db_query

        logger.debug(f"SQL request:\n{query}")

    def send_request(self, trace=False):
        response_status = False

        try:
            self._debug_sql_query_printout()
            if isinstance(self.db_query, tuple):
                response = self.clickhouse_client.execute(
                    self.db_query[0], self.db_query[1]
                )
            else:
                response = self.clickhouse_client.execute(self.db_query)
            response_status = True
            logger.debug(f"SQL request elapsed {self.clickhouse_client.last_query.elapsed:.3f} seconds")
        except Exception as error:
            if issubclass(error.__class__, errors.Error):
                logger.error(exception_to_logger(error))
                response = json_str_error("Error in SQL query!")
                if trace:
                    print_statusbar([(error, 'd',)])
            else:
                raise error

        return response_status, response

    def disconnect(self):
        self.clickhouse_client.disconnect()
        self.connection_status = False


class Connection:
    """Database connection class supports retries if connection to dabase have been lost."""
    
    def __init__(self, request_line=None):
        self.request_line = request_line
        self.db_connection = DBConnection(
            settings.DATABASE_HOST,
            settings.DATABASE_NAME,
            settings.DATABASE_USER,
            settings.DATABASE_PASS,
        )

    def send_request(self, trace=False):
        status = self.db_connection.connection_status
        if not status:
            for try_ in range(settings.TRY_CONNECTION_NUMBER):
                logger.debug("Attempt to connect to the database #{}".format(try_ + 1))

                status = self.db_connection.make_connection()
                if status:
                    break

                sleep(settings.TRY_TIMEOUT)

        if status:
            self.db_connection.db_query = self.request_line
            return self.db_connection.send_request(trace)
        else:
            return False, "Database connection error."

    def drop_connection(self):
        if self.db_connection:
            self.db_connection.disconnect()
            logger.debug("Connection closed.")
